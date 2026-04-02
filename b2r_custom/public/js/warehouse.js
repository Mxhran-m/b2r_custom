frappe.ui.form.on("Warehouse", {
	refresh(frm) {
		applyCapacityFieldDescriptions(frm);
		renderCapacitySummary(frm);

		if (!frm.is_new() && !frm.doc.is_group) {
			frm.add_custom_button(__("Refresh Occupancy"), () => refreshOccupancy(frm));
		}
	},

	total_sq_ft(frm) {
		renderCapacitySummary(frm);
	},

	used_sq_ft(frm) {
		renderCapacitySummary(frm);
	},

	is_group(frm) {
		renderCapacitySummary(frm);
	},
});

function applyCapacityFieldDescriptions(frm) {
	frm.set_df_property(
		"total_sq_ft",
		"description",
		__("Set the full storage capacity for this warehouse in square feet.")
	);
	frm.set_df_property(
		"used_sq_ft",
		"description",
		__("This value is calculated from current stock and item space consumption.")
	);
}

function renderCapacitySummary(frm) {
	if (frm.doc.is_group) {
		frm.set_intro(__("Capacity tracking is only relevant for leaf warehouses, not warehouse groups."), "blue");
		return;
	}

	const total = frappe.utils.flt(frm.doc.total_sq_ft);
	const used = frappe.utils.flt(frm.doc.used_sq_ft);

	if (!total) {
		frm.set_intro(
			__("Set <b>Total Sq Ft</b> to enable capacity checks on Purchase Receipts and Stock Entries."),
			"blue"
		);
		return;
	}

	const occupancy = total ? (used / total) * 100 : 0;
	const remaining = Math.max(total - used, 0);
	const indicator = occupancy >= 90 ? "red" : occupancy >= 80 ? "orange" : "green";

	frm.set_intro(
		__(
			"Occupancy: <b>{0}%</b> | Used: <b>{1}</b> sq ft | Remaining: <b>{2}</b> sq ft",
			[
				window.b2rCustom.formatFloat(occupancy),
				window.b2rCustom.formatFloat(used),
				window.b2rCustom.formatFloat(remaining),
			]
		),
		indicator
	);
}

function refreshOccupancy(frm) {
	frappe.call({
		method: "b2r_custom.api.get_warehouse_occupancy",
		args: {
			warehouse: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Refreshing warehouse occupancy..."),
		callback: ({ message }) => {
			const row = Array.isArray(message) ? message[0] : null;
			if (!row) {
				frappe.show_alert({ message: __("No occupancy data found."), indicator: "orange" });
				return;
			}

			frm.set_value("used_sq_ft", row.used_sq_ft || 0);
			renderCapacitySummary(frm);
			frappe.show_alert({ message: __("Warehouse occupancy refreshed."), indicator: "green" });
		},
	});
}
