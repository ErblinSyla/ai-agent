def score_report(criteria, awarded):
    known = {c["id"]: c for c in criteria}
    extra = set(awarded) - known.keys()
    if extra: raise ValueError(f"Unknown rubric criteria: {sorted(extra)}")
    details=[]
    for cid,c in known.items():
        maximum=float(c["max_points"]); value=float(awarded.get(cid,0))
        if not 0 <= value <= maximum: raise ValueError(f"Score for {cid} must be between 0 and {maximum}")
        details.append({"id":cid,"awarded":value,"maximum":maximum,"reason":c.get("description","")})
    return {"criteria":details,"total":sum(x["awarded"] for x in details),"maximum":sum(x["maximum"] for x in details)}
