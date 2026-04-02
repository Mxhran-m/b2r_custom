from b2r_custom.api import ensure_customizations


def after_install():
	ensure_customizations()
