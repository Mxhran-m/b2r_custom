window.b2rCustom = window.b2rCustom || {};

window.b2rCustom.formatFloat = function formatFloat(value) {
	return frappe.format(value || 0, { fieldtype: "Float", precision: 2 });
};
