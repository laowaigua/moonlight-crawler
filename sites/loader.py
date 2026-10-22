import pkgutil
import importlib
import sys

def list_site():
    """返回 sites 目录下有 base.py 的站点名"""
    import sites

    if sites.__path__[0] in sys.path_importer_cache:
        del sys.path_importer_cache[sites.__path__[0]]

    site_list = []

    for finder, name, ispkg in pkgutil.iter_modules(sites.__path__):
        if not ispkg:
            continue
        # 检查 base.py 是否存在
        try:
            importlib.import_module(f"sites.{name}.parser")
            site_list.append(name)
        except ModuleNotFoundError as e:
            print(f"跳过站点 '{name}': 无法导入 parser 模块，原因: {e}")
            continue

    return site_list


def load_parser(site: str):
    try:
        module = importlib.import_module(f"sites.{site}.parser")
    except ModuleNotFoundError:
        raise ValueError(f"站点模块不存在：{site}")

    return module.Parser

def list_schema():
    """返回 sites 目录下有 schema.py 的站点名"""
    import sites
    sites_list = []

    for finder, name, ispkg in pkgutil.iter_modules(sites.__path__):
        if not ispkg:
            continue
        # 检查 base.py 是否存在
        try:
            importlib.import_module(f"sites.{name}.schema")
            sites_list.append(name)
        except ModuleNotFoundError:
            continue

    return sites_list

def load_schema(site: str):
    try:
        module = importlib.import_module(f"sites.{site}.schema")
    except ModuleNotFoundError:
        raise ValueError(f"{site} 缺少 schema")

    return module.SCHEMA