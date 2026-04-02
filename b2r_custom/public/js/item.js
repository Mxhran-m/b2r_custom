frappe.ui.form.on("Item", {
	refresh(frm) {
		applySpaceFieldGuidance(frm);
		renderSpaceSummary(frm);
	},

	product_space_unit(frm) {
		renderSpaceSummary(frm);
	},

	is_stock_item(frm) {
		renderSpaceSummary(frm);
	},
});

function applySpaceFieldGuidance(frm) {
	frm.set_df_property(
		"product_space_unit",
		"description",
		__("Enter how many square feet one unit of this item consumes in warehouse storage.")
	);
}

function renderSpaceSummary(frm) {
	if (!frm.doc.is_stock_item) {
		frm.set_intro(__("Storage space tracking is only relevant for stock items."), "blue");
		return;
	}

	const spacePerUnit = frappe.utils.flt(frm.doc.product_space_unit);
	if (!spacePerUnit) {
		frm.set_intro(
			__(
				"Set <b>Space Required Per Unit (Sq Ft)</b> so warehouse occupancy is calculated automatically for this item."
			),
			"blue"
		);
		return;
	}

	frm.set_intro(
		__(
			"Each unit of this item consumes <b>{0}</b> sq ft of warehouse space.",
			[formatItemNumber(spacePerUnit)]
		),
		"green"
	);
}

function formatItemNumber(value) {
	return frappe.format(value || 0, { fieldtype: "Float", precision: 2 });
}
