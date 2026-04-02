from __future__ import annotations

import hashlib
import html
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, flt, getdate
from frappe.utils.file_manager import get_file

SPACE_WARNING_THRESHOLDS = (80, 90)
WITHOUT_BILLING = "Without Billing"
WITH_BILLING = "With Billing"
RESERVATION_FIELDNAME = "stock_reserved_on_payment"


def ensure_customizations():
	for custom_field in get_custom_field_definitions():
		_sync_custom_field(custom_field)


def get_custom_field_definitions():
	fixtures_path = Path(__file__).resolve().parent / "fixtures" / "custom_field.json"
	with fixtures_path.open(encoding="utf-8") as fixture_file:
		return json.load(fixture_file)


def validate_inbound_capacity(doc: Document, method: str | None = None):
	if doc.doctype not in {"Purchase Receipt", "Stock Entry"}:
		return

	additional_space_by_warehouse = _get_inbound_space_requirements(doc)
	if not additional_space_by_warehouse:
		return

	warehouse_names = list(additional_space_by_warehouse)
	warehouse_capacity_map = frappe._dict(
		{
			row.name: row
			for row in frappe.get_all(
				"Warehouse",
				filters={"name": ("in", warehouse_names)},
				fields=["name", "warehouse_name", "total_sq_ft"],
			)
		}
	)

	for warehouse, additional_space in additional_space_by_warehouse.items():
		warehouse_doc = warehouse_capacity_map.get(warehouse)
		total_sq_ft = flt(warehouse_doc.total_sq_ft) if warehouse_doc else 0
		if total_sq_ft <= 0:
			continue

		current_usage = get_warehouse_used_sq_ft(warehouse)
		projected_usage = current_usage + additional_space
		occupancy_pct = (projected_usage / total_sq_ft) * 100 if total_sq_ft else 0

		if projected_usage > total_sq_ft:
			frappe.throw(
				_(
					"Warehouse {0} exceeds capacity. Current usage is {1} sq ft, incoming stock adds {2} sq ft, but total capacity is {3} sq ft."
				).format(
					frappe.bold(warehouse_doc.warehouse_name if warehouse_doc else warehouse),
					frappe.bold(flt(current_usage, 2)),
					frappe.bold(flt(additional_space, 2)),
					frappe.bold(flt(total_sq_ft, 2)),
				)
			)

		for threshold in reversed(SPACE_WARNING_THRESHOLDS):
			if occupancy_pct >= threshold:
				frappe.msgprint(
					_(
						"Warehouse {0} is projected to reach {1}% occupancy after this transaction."
					).format(
						frappe.bold(warehouse_doc.warehouse_name if warehouse_doc else warehouse),
						frappe.bold(flt(occupancy_pct, 2)),
					),
					title=_("Warehouse Capacity Warning"),
					indicator="orange",
					alert=True,
				)
				break


def handle_stock_impact_submit(doc: Document, method: str | None = None):
	sync_warehouse_usage_for_doc(doc)


def handle_stock_impact_cancel(doc: Document, method: str | None = None):
	sync_warehouse_usage_for_doc(doc)


def handle_sales_invoice_submit(doc: Document, method: str | None = None):
	if cint(doc.get("update_stock")):
		sync_warehouse_usage_for_doc(doc)


def handle_sales_invoice_cancel(doc: Document, method: str | None = None):
	if cint(doc.get("update_stock")):
		sync_warehouse_usage_for_doc(doc)

	if cint(doc.get(RESERVATION_FIELDNAME)):
		release_reserved_stock_for_invoice(doc)


def validate_sales_invoice(doc: Document, method: str | None = None):
	_ensure_credit_limit_is_blocking(doc)
	_validate_billing_mode(doc)
	_apply_accounting_dimension(doc)


def reserve_stock_on_payment(doc: Document, method: str | None = None):
	for sales_invoice in _get_referenced_sales_invoices(doc):
		lock_name = f"b2r_custom:reservation:{sales_invoice}"
		with frappe.cache().get_lock(lock_name, timeout=30):
			invoice = frappe.get_doc("Sales Invoice", sales_invoice)
			if invoice.docstatus != 1 or cint(invoice.get(RESERVATION_FIELDNAME)):
				continue

			_adjust_invoice_item_reservation(invoice, direction=1)
			invoice.db_set(RESERVATION_FIELDNAME, 1, update_modified=False)


def release_stock_on_payment_cancel(doc: Document, method: str | None = None):
	for sales_invoice in _get_referenced_sales_invoices(doc):
		lock_name = f"b2r_custom:reservation:{sales_invoice}"
		with frappe.cache().get_lock(lock_name, timeout=30):
			invoice = frappe.get_doc("Sales Invoice", sales_invoice)
			if not cint(invoice.get(RESERVATION_FIELDNAME)):
				continue
			if _has_other_submitted_payments(invoice.name, exclude_payment_entry=doc.name):
				continue

			_release_reserved_stock_for_invoice_locked(invoice)


def release_reserved_stock_for_invoice(invoice: Document):
	lock_name = f"b2r_custom:reservation:{invoice.name}"
	with frappe.cache().get_lock(lock_name, timeout=30):
		_release_reserved_stock_for_invoice_locked(invoice)


def validate_employee_checkin(doc: Document, method: str | None = None):
	if not cstr(doc.get("checkin_image_hash")).strip():
		frappe.throw(_("Check-in image is required for Employee Checkin."))

	if not cstr(doc.get("geolocation")).strip():
		frappe.throw(_("Geolocation is required for Employee Checkin."))

	employee_image = cstr(frappe.db.get_value("Employee", doc.employee, "face_image_hash")).strip()
	checkin_image = cstr(doc.get("checkin_image_hash")).strip()
	if not employee_image:
		frappe.throw(_("Face image is required on the Employee record before check-in validation can run."))

	employee_hash = _get_image_content_hash(employee_image)
	checkin_hash = _get_image_content_hash(checkin_image)
	if employee_hash != checkin_hash:
		frappe.throw(_("Check-in image does not match the employee face image."))


def validate_attendance(doc: Document, method: str | None = None):
	if not cstr(doc.get("checkin_geolocation")).strip():
		geolocation = _get_attendance_geolocation(doc.employee, doc.attendance_date)
		if geolocation:
			doc.checkin_geolocation = geolocation

	if not cstr(doc.get("checkin_geolocation")).strip():
		frappe.throw(_("Check-in geolocation is required for Attendance."))


def send_vendor_aging_reminders():
	recipients = _get_vendor_aging_recipients()
	if not recipients:
		return

	rows = frappe.db.sql(
		"""
		select
			name,
			supplier,
			company,
			due_date,
			outstanding_amount,
			datediff(curdate(), due_date) as overdue_days
		from `tabPurchase Invoice`
		where docstatus = 1
			and outstanding_amount > 0
			and due_date is not null
			and due_date <= curdate()
		order by overdue_days desc, outstanding_amount desc
		""",
		as_dict=True,
	)
	if not rows:
		return

	buckets = {
		"0-30 Days": [],
		"31-60 Days": [],
		"61+ Days": [],
	}
	for row in rows:
		if row.overdue_days <= 30:
			buckets["0-30 Days"].append(row)
		elif row.overdue_days <= 60:
			buckets["31-60 Days"].append(row)
		else:
			buckets["61+ Days"].append(row)

	lines = [
		"<p>Outstanding vendor balances require attention.</p>",
	]
	for label, bucket_rows in buckets.items():
		if not bucket_rows:
			continue
		lines.append(f"<p><strong>{label}</strong></p>")
		lines.append("<ul>")
		for row in bucket_rows[:20]:
			lines.append(
				f"<li>{_escape_html(row.supplier)} / {_escape_html(row.company)} / {_escape_html(row.name)} / Due {_escape_html(row.due_date)} / Outstanding {_escape_html(flt(row.outstanding_amount, 2))}</li>"
			)
		lines.append("</ul>")

	frappe.sendmail(
		recipients=recipients,
		subject=_("Vendor Aging Reminder"),
		message="".join(lines),
		now=True,
	)


@frappe.whitelist()
def get_warehouse_occupancy(warehouse: str | None = None):
	filters = {}
	if warehouse:
		filters["name"] = warehouse

	warehouses = frappe.get_all("Warehouse", filters=filters, fields=["name", "warehouse_name", "total_sq_ft"])
	for row in warehouses:
		row.used_sq_ft = get_warehouse_used_sq_ft(row.name)
		row.occupancy_pct = (flt(row.used_sq_ft) / flt(row.total_sq_ft) * 100) if flt(row.total_sq_ft) else 0
	return warehouses


@frappe.whitelist()
def get_fast_moving_stock(warehouse: str | None = None, days: int = 30, limit: int = 20):
	days = max(cint(days), 1)
	limit = max(cint(limit), 1)
	params = {"days": days, "limit": limit}
	warehouse_filter = ""
	if warehouse:
		params["warehouse"] = warehouse
		warehouse_filter = " and sle.warehouse = %(warehouse)s"

	return frappe.db.sql(
		f"""
		select
			sle.item_code,
			sum(abs(sle.actual_qty)) as moved_qty,
			count(*) as movement_count
		from `tabStock Ledger Entry` sle
		where sle.is_cancelled = 0
			and sle.actual_qty < 0
			and sle.posting_date >= date_sub(curdate(), interval %(days)s day)
			{warehouse_filter}
		group by sle.item_code
		order by moved_qty desc
		limit %(limit)s
		""",
		params,
		as_dict=True,
	)


def sync_warehouse_usage_for_doc(doc: Document):
	for warehouse in _get_affected_warehouses(doc):
		used_sq_ft = get_warehouse_used_sq_ft(warehouse)
		frappe.db.set_value("Warehouse", warehouse, "used_sq_ft", used_sq_ft, update_modified=False)


def sync_all_warehouse_usage():
	for warehouse in frappe.get_all("Warehouse", pluck="name"):
		frappe.db.set_value("Warehouse", warehouse, "used_sq_ft", get_warehouse_used_sq_ft(warehouse), update_modified=False)


def get_warehouse_used_sq_ft(warehouse: str) -> float:
	result = frappe.db.sql(
		"""
		select coalesce(sum(case when b.actual_qty > 0 then b.actual_qty else 0 end * coalesce(i.product_space_unit, 0)), 0)
		from `tabBin` b
		inner join `tabItem` i on i.name = b.item_code
		where b.warehouse = %s
		""",
		(warehouse,),
	)
	return flt(result[0][0]) if result else 0


def _get_inbound_space_requirements(doc: Document) -> dict[str, float]:
	item_codes = {row.item_code for row in doc.get("items", []) if row.item_code}
	if not item_codes:
		return {}

	product_space_map = frappe._dict(
		{
			row.name: flt(row.product_space_unit)
			for row in frappe.get_all(
				"Item",
				filters={"name": ("in", list(item_codes))},
				fields=["name", "product_space_unit"],
			)
		}
	)

	space_by_warehouse = defaultdict(float)
	for row in doc.get("items", []):
		warehouse, quantity = _get_inbound_target_and_qty(doc.doctype, row)
		if not warehouse or quantity <= 0:
			continue
		space_by_warehouse[warehouse] += quantity * product_space_map.get(row.item_code, 0)

	return dict(space_by_warehouse)


def _get_inbound_target_and_qty(doctype: str, row: Document) -> tuple[str | None, float]:
	if doctype == "Purchase Receipt":
		return row.get("warehouse"), flt(row.get("qty"))

	if doctype == "Stock Entry":
		return row.get("t_warehouse"), flt(row.get("transfer_qty") or row.get("qty"))

	return None, 0


def _get_affected_warehouses(doc: Document) -> list[str]:
	warehouses: set[str] = set()
	for row in doc.get("items", []):
		for fieldname in ("warehouse", "t_warehouse", "s_warehouse"):
			if row.get(fieldname):
				warehouses.add(row.get(fieldname))
	return sorted(warehouses)


def _ensure_credit_limit_is_blocking(doc: Document):
	if not doc.customer or not doc.company or doc.is_return:
		return

	from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding

	credit_limit = flt(get_credit_limit(doc.customer, doc.company))
	if credit_limit <= 0:
		return

	customer_outstanding = flt(
		get_customer_outstanding(doc.customer, doc.company, _get_ignore_outstanding_sales_order(doc))
	)
	projected_outstanding = customer_outstanding + _get_invoice_exposure(doc)
	if projected_outstanding > credit_limit:
		frappe.throw(
			_(
				"Sales Invoice is blocked because customer {0} exceeds the credit limit. Outstanding after this invoice would be {1}, while the configured limit is {2}."
			).format(
				frappe.bold(doc.customer),
				frappe.bold(flt(projected_outstanding, 2)),
				frappe.bold(flt(credit_limit, 2)),
			),
			title=_("Credit Limit Exceeded"),
		)


def _get_ignore_outstanding_sales_order(doc: Document) -> bool:
	if not doc.customer or not doc.company:
		return False

	return bool(
		frappe.db.get_value(
			"Customer Credit Limit",
			filters={"parent": doc.customer, "parenttype": "Customer", "company": doc.company},
			fieldname="bypass_credit_limit_check",
		)
	)


def _get_invoice_exposure(doc: Document) -> float:
	grand_total = Decimal(str(flt(doc.grand_total)))
	advance_total = Decimal(str(flt(doc.total_advance)))
	write_off_total = Decimal(str(flt(doc.write_off_amount)))
	paid_total = Decimal(str(flt(doc.paid_amount)))
	exposure = grand_total - advance_total - write_off_total - paid_total
	return flt(max(exposure, Decimal("0")))


def _validate_billing_mode(doc: Document):
	billing_mode = cstr(doc.get("billing_mode")).strip()
	if billing_mode not in {WITH_BILLING, WITHOUT_BILLING}:
		return

	item_codes = {row.item_code for row in doc.get("items", []) if row.item_code}
	if not item_codes:
		return

	branded_map = frappe._dict(
		{
			row.name: cint(row.is_branded)
			for row in frappe.get_all("Item", filters={"name": ("in", list(item_codes))}, fields=["name", "is_branded"])
		}
	)

	if billing_mode == WITH_BILLING:
		non_branded_items = [row.item_code for row in doc.items if row.item_code and not branded_map.get(row.item_code)]
		if non_branded_items:
			frappe.throw(
				_(
					"With Billing invoices can only contain branded items. Non-branded items found: {0}"
				).format(", ".join(sorted(set(non_branded_items))))
			)

		if not _has_gst_applied(doc):
			frappe.throw(_("With Billing invoices require GST tax rows on the Sales Invoice."))


def _has_gst_applied(doc: Document) -> bool:
	for tax in doc.get("taxes", []):
		account_head = cstr(tax.get("account_head")).lower()
		description = cstr(tax.get("description")).lower()
		if "gst" in account_head or "gst" in description:
			return True
	return False


def _apply_accounting_dimension(doc: Document):
	dimension_field = cstr(frappe.conf.get("b2r_billing_dimension_field")).strip()
	if not dimension_field or not doc.meta.has_field(dimension_field):
		return

	if doc.billing_mode not in {WITH_BILLING, WITHOUT_BILLING}:
		return

	dimension_value = WITH_BILLING if doc.billing_mode == WITH_BILLING else WITHOUT_BILLING
	doc.set(dimension_field, dimension_value)


def _get_referenced_sales_invoices(doc: Document) -> list[str]:
	references = []
	for row in doc.get("references", []):
		if row.reference_doctype == "Sales Invoice" and row.reference_name and flt(row.allocated_amount) > 0:
			references.append(row.reference_name)
	return sorted(set(references))


def _adjust_invoice_item_reservation(invoice: Document, direction: int):
	if direction not in {1, -1}:
		return

	item_rows = defaultdict(float)
	for row in invoice.get("items", []):
		warehouse = row.get("warehouse") or invoice.get("set_warehouse")
		if not warehouse or not row.item_code:
			continue
		item_rows[(row.item_code, warehouse)] += flt(row.qty) * direction

	for (item_code, warehouse), qty_delta in item_rows.items():
		if qty_delta:
			_update_reserved_qty(item_code, warehouse, qty_delta)


def _release_reserved_stock_for_invoice_locked(invoice: Document):
	if not cint(invoice.get(RESERVATION_FIELDNAME)):
		return

	_adjust_invoice_item_reservation(invoice, direction=-1)
	invoice.db_set(RESERVATION_FIELDNAME, 0, update_modified=False)


def _update_reserved_qty(item_code: str, warehouse: str, qty_delta: float):
	bin_name = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "name")
	if not bin_name:
		return

	current_reserved_qty = flt(frappe.db.get_value("Bin", bin_name, "reserved_qty"))
	new_reserved_qty = max(current_reserved_qty + qty_delta, 0)
	frappe.db.set_value("Bin", bin_name, "reserved_qty", new_reserved_qty, update_modified=False)


def _has_other_submitted_payments(sales_invoice: str, exclude_payment_entry: str | None = None) -> bool:
	references = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Invoice", "reference_name": sales_invoice},
		fields=["parent"],
	)
	if not references:
		return False

	parents = [row.parent for row in references if row.parent and row.parent != exclude_payment_entry]
	if not parents:
		return False

	return bool(frappe.db.exists("Payment Entry", {"name": ("in", parents), "docstatus": 1}))


def _get_attendance_geolocation(employee: str, attendance_date) -> str | None:
	if not employee or not attendance_date:
		return None

	start = f"{getdate(attendance_date)} 00:00:00"
	end = f"{getdate(attendance_date)} 23:59:59"
	checkin = frappe.db.sql(
		"""
		select geolocation
		from `tabEmployee Checkin`
		where employee = %s
			and time between %s and %s
			and ifnull(geolocation, '') != ''
		order by time desc
		limit 1
		""",
		(employee, start, end),
		as_dict=True,
	)
	return checkin[0].geolocation if checkin else None


def _get_vendor_aging_recipients() -> list[str]:
	recipients: set[str] = set()
	for role in ("Accountant", "Accounts Manager", "Accounts User"):
		if not frappe.db.exists("Role", role):
			continue
		users = frappe.get_all(
			"Has Role",
			filters={"role": role},
			distinct=True,
			pluck="parent",
		)
		if not users:
			continue

		emails = frappe.get_all("User", filters={"name": ("in", users), "enabled": 1}, pluck="email")
		recipients.update(email for email in emails if email)

	return sorted(recipients)


def _escape_html(value) -> str:
	return html.escape(cstr(value), quote=True)


def _get_image_content_hash(file_url: str) -> str:
	try:
		_, content = get_file(file_url)
	except (FileNotFoundError, OSError, frappe.DoesNotExistError) as error:
		frappe.log_error(
			title="B2R Face Image Read Failed",
			message=frappe.get_traceback(with_context=True),
		)
		frappe.throw(_("Unable to read image file {0}.").format(frappe.bold(file_url)))
	except Exception:
		frappe.log_error(
			title="B2R Face Image Read Failed",
			message=frappe.get_traceback(with_context=True),
		)
		raise

	if isinstance(content, str):
		content = content.encode()

	return hashlib.sha256(content).hexdigest()


def _sync_custom_field(custom_field: dict):
	field_data = {key: value for key, value in custom_field.items() if key not in {"doctype", "name"}}
	existing_name = frappe.db.get_value(
		"Custom Field",
		{"dt": custom_field["dt"], "fieldname": custom_field["fieldname"]},
		"name",
	)

	if existing_name:
		custom_doc = frappe.get_doc("Custom Field", existing_name)
		custom_doc.update(field_data)
		custom_doc.flags.ignore_validate = True
		custom_doc.save(ignore_permissions=True)
		return

	custom_doc = frappe.get_doc({"doctype": "Custom Field", **field_data})
	custom_doc.insert(ignore_permissions=True)
