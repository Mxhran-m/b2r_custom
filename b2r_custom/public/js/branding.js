(function () {
	const BRAND_NAME = "B2R Custom ERP";
	const LOGO_URL = "/assets/b2r_custom/img/b2r-logo.svg";
	const FAVICON_URL = "/assets/b2r_custom/img/b2r-mark.svg";

	function replaceBranding(root = document) {
		replaceText(root);
		replaceLogoImages(root);
		replaceFooterLinks(root);
		setDocumentTitle();
		setFavicon();
	}

	function replaceText(root) {
		const selectors = [
			".app-logo .app-title",
			".navbar-home",
			".page-card-head h4",
			".login-content .page-card-head h4",
			".sidebar-item-label",
		];

		for (const selector of selectors) {
			root.querySelectorAll(selector).forEach((node) => {
				const text = (node.textContent || "").trim();
				if (text === "ERPNext" || text === "Frappe" || text === "Welcome Back") {
					node.textContent = BRAND_NAME;
				}
			});
		}
	}

	function replaceLogoImages(root) {
		root.querySelectorAll("img").forEach((image) => {
			const source = image.getAttribute("src") || "";
			const alt = image.getAttribute("alt") || "";
			if (
				source.includes("erpnext") ||
				source.includes("frappe") ||
				alt.includes("ERPNext") ||
				alt.includes("Frappe")
			) {
				image.setAttribute("src", LOGO_URL);
				image.setAttribute("alt", BRAND_NAME);
			}
		});
	}

	function replaceFooterLinks(root) {
		root.querySelectorAll('a[href*="frappe"], a[href*="erpnext"]').forEach((anchor) => {
			anchor.textContent = BRAND_NAME;
			anchor.setAttribute("href", "#");
		});
	}

	function setDocumentTitle() {
		if (document.title.includes("ERPNext") || document.title.includes("Frappe")) {
			document.title = document.title.replace(/ERPNext|Frappe/g, BRAND_NAME);
		} else if (!document.title.includes(BRAND_NAME)) {
			document.title = `${BRAND_NAME} | ${document.title}`;
		}
	}

	function setFavicon() {
		const favicon = document.querySelector('link[rel*="icon"]');
		if (favicon) {
			favicon.setAttribute("href", FAVICON_URL);
		}
	}

	function boot() {
		replaceBranding(document);
		const observer = new MutationObserver(() => replaceBranding(document));
		observer.observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", boot);
	} else {
		boot();
	}
})();
