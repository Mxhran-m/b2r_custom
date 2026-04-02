from b2r_custom.api import ensure_customizations, sync_all_warehouse_usage


def execute():
	ensure_customizations()
	sync_all_warehouse_usage()
