(function () {
	const BRAND_NAME = "B2R Custom ERP";
	const LOGO_URL = "/assets/b2r_custom/img/b2r-logo.svg";
	const FAVICON_URL = "/assets/b2r_custom/img/b2r-mark.svg";
	const TEXT_SELECTORS = [
		".app-logo .app-title",
		".navbar-home",
		".page-card-head h4",
		".login-content .page-card-head h4",
		".sidebar-item-label",
	];
	const LOGO_SELECTORS = [
		".app-logo img",
		".navbar-home img",
		".page-card-head img",
		".login-content img",
	];
	const FOOTER_LINK_SELECTORS = [
		".page-footer a[href*='frappe']",
		".page-footer a[href*='erpnext']",
		".footer-powered a[href*='frappe']",
		".footer-powered a[href*='erpnext']",
	];

	function replaceBranding(root = document) {
		replaceText(root);
		replaceLogoImages(root);
		replaceFooterLinks(root);
		setDocumentTitle();
		setFavicon();
	}

	function replaceText(root) {
		for (const selector of TEXT_SELECTORS) {
			root.querySelectorAll(selector).forEach((node) => {
				const text = (node.textContent || "").trim();
				if (text === "ERPNext" || text === "Frappe" || text === "Welcome Back") {
					node.textContent = BRAND_NAME;
				}
			});
		}
	}

	function replaceLogoImages(root) {
		for (const selector of LOGO_SELECTORS) {
			root.querySelectorAll(selector).forEach((image) => {
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
	}

	function replaceFooterLinks(root) {
		for (const selector of FOOTER_LINK_SELECTORS) {
			root.querySelectorAll(selector).forEach((anchor) => {
				const container = anchor.closest(".page-footer, .footer-powered") || anchor.parentElement;
				if (container) {
					container.textContent = BRAND_NAME;
				} else {
					anchor.remove();
				}
			});
		}
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

	function debounce(fn, delay) {
		let timeoutId;
		return function debounced(...args) {
			if (timeoutId) {
				clearTimeout(timeoutId);
			}
			timeoutId = setTimeout(() => {
				timeoutId = null;
				fn.apply(this, args);
			}, delay);
		};
	}

	function mutationNeedsBrandingPass(mutations) {
		return mutations.some((mutation) => {
			if (!mutation.addedNodes || mutation.addedNodes.length === 0) {
				return false;
			}

			return [...mutation.addedNodes]
				.filter((node) => node.nodeType === Node.ELEMENT_NODE)
				.some((node) => {
					if (node.matches?.(TEXT_SELECTORS.join(", "))) {
						return true;
					}
					if (node.matches?.(LOGO_SELECTORS.join(", "))) {
						return true;
					}
					if (node.matches?.(FOOTER_LINK_SELECTORS.join(", "))) {
						return true;
					}
					return Boolean(
						node.querySelector?.(
							`${TEXT_SELECTORS.join(", ")}, ${LOGO_SELECTORS.join(", ")}, ${FOOTER_LINK_SELECTORS.join(", ")}`
						)
					);
				});
		});
	}

	function boot() {
		replaceBranding(document);
		const scheduleReplaceBranding = debounce(() => replaceBranding(document), 100);
		const observer = new MutationObserver((mutations) => {
			if (mutationNeedsBrandingPass(mutations)) {
				scheduleReplaceBranding();
			}
		});
		observer.observe(document.body, { childList: true, subtree: true });
	}

	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", boot);
	} else {
		boot();
	}
})();
