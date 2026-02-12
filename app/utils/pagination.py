# app/utils/pagination.py
def parse_pagination(req, default_page=1, default_per_page=20, max_per_page=100):
    try:
        page = max(int(req.args.get("page", default_page)), 1)
        per_page = min(max(int(req.args.get("per_page", default_per_page)), 1), max_per_page)
        return page, per_page
    except ValueError:
        return default_page, default_per_page
