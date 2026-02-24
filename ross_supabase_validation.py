#!/usr/bin/env python3
"""
Ross Semi-Deterministic Validation — Supabase Live Data
Uses supabase-py (already in your venv) to avoid macOS SSL issues.
"""

import math
import json
import csv
import os
import sys
from collections import defaultdict

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold
from sklearn.preprocessing import OrdinalEncoder
from supabase import create_client

SUPABASE_URL = "https://dernxirzvawjmdxzxefl.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ═══ ROSS EQUIPMENT CONSTANTS ═══
ROSS_HP200K_RATE = 409.0
ROSS_HP200K_SETUP_HRS = 0.25
ROSS_HP200K_SETUP_FT = 50
ROSS_HP200K_SPOILAGE = 0.008
ROSS_HP200K_CLICK_CMYOVG = 0.0394
ROSS_HP200K_CLICK_WHITE = 0.01917
ROSS_HP200K_PRIMING = 0.07
ROSS_HP200K_PITCH = 0.125
ROSS_HP200K_MAX_REPEAT = 43.0
ROSS_HP200K_MAX_STOCK_WIDTH = 30.0
ROSS_HP200K_MIN_STOCK_WIDTH = 15.75
ROSS_HP200K_TRIM_WIDTH = 0.25
ROSS_HP200K_SHEETS_PER_MIN = 31.9
ROSS_CONVERTING_PER_POUCH = 0.055
ROSS_ZIPPER_COST_PER_MSI = 5.258772
ROSS_ZIPPER_WIDTH = 0.95

def calc_msi(w, l):
    return w * l * 12 / 1000

def calc_ross_layout(width, height, gusset):
    pw = height * 2 + gusset
    sa = pw + ROSS_HP200K_TRIM_WIDTH
    na = max(1, int(ROSS_HP200K_MAX_STOCK_WIDTH / sa))
    sw = max(ROSS_HP200K_MIN_STOCK_WIDTH, min(sa * na, ROSS_HP200K_MAX_STOCK_WIDTH))
    mg = int(ROSS_HP200K_MAX_REPEAT / ROSS_HP200K_PITCH)
    bg, ba = None, 0
    for g in range(1, mg + 1):
        r = g * ROSS_HP200K_PITCH
        a = int(r / width)
        if a > ba and r <= ROSS_HP200K_MAX_REPEAT:
            ba = a; bg = g
    if bg is None:
        bg = int(width / ROSS_HP200K_PITCH) + 1; ba = 1
    return {"no_across": na, "no_around": ba, "repeat_ft": bg * ROSS_HP200K_PITCH / 12.0,
            "stock_width": sw, "labels_per_cycle": na * ba}

def calculate_ross_known_cost(width, height, gusset, quantity, has_zipper=True):
    L = calc_ross_layout(width, height, gusset)
    if L["labels_per_cycle"] == 0: return None
    gs = math.ceil(quantity / L["labels_per_cycle"])
    ss = math.ceil(gs * ROSS_HP200K_SPOILAGE)
    su = math.ceil(ROSS_HP200K_SETUP_FT / L["repeat_ft"]) if L["repeat_ft"] > 0 else 0
    tf = gs + ss + su
    sl = tf * L["repeat_ft"]
    cc = tf * 2 * 4 * ROSS_HP200K_CLICK_CMYOVG + tf * 2 * 1 * ROSS_HP200K_CLICK_WHITE
    pc = calc_msi(L["stock_width"], sl) * ROSS_HP200K_PRIMING
    hm = ROSS_HP200K_RATE * ROSS_HP200K_SETUP_HRS
    sf = ROSS_HP200K_SHEETS_PER_MIN * L["repeat_ft"]
    hr = max(0, sl - ROSS_HP200K_SETUP_FT) / (sf * 60) if sf > 0 else 0
    hrc = hr * ROSS_HP200K_RATE
    cv = ROSS_CONVERTING_PER_POUCH * quantity
    zc = ROSS_ZIPPER_COST_PER_MSI * (width * ROSS_ZIPPER_WIDTH / 1000) * quantity if has_zipper else 0.0
    kt = cc + pc + hm + hrc + cv + zc
    return {"known_total": kt, "known_unit": kt/quantity if quantity > 0 else 0,
            "click_cost": cc, "priming_cost": pc, "hp_makeready": hm, "hp_run_cost": hrc,
            "converting_cost": cv, "zipper_cost": zc, "stock_length_ft": sl,
            "no_across": L["no_across"], "no_around": L["no_around"],
            "stock_width": L["stock_width"], "labels_per_cycle": L["labels_per_cycle"]}

def run():
    global SUPABASE_KEY
    if not SUPABASE_KEY:
        SUPABASE_KEY = input("Enter SUPABASE_KEY: ").strip()
    print("=" * 70)
    print("ROSS SEMI-DETERMINISTIC — LIVE SUPABASE VALIDATION")
    print("=" * 70)
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("\n── Fetching Ross Quotes ──")
    resp = client.table("quotes").select(
        "id,fl_number,vendor,width,height,gusset,substrate,finish,seal_type,zipper,tear_notch,hole_punch,corner_treatment,created_at"
    ).eq("vendor", "ross").execute()
    quotes = resp.data
    print(f"  Ross quotes: {len(quotes)}")
    if not quotes: print("No Ross quotes found!"); return

    print("  Fetching quote prices...")
    qids = [q["id"] for q in quotes]
    all_prices = []
    for i in range(0, len(qids), 50):
        resp = client.table("quote_prices").select(
            "quote_id,quantity,unit_price,total_price"
        ).in_("quote_id", qids[i:i+50]).execute()
        all_prices.extend(resp.data)
    print(f"  Price rows: {len(all_prices)}")

    qmap = {q["id"]: q for q in quotes}
    rows = []
    for p in all_prices:
        q = qmap.get(p["quote_id"])
        if not q: continue
        rows.append({
            "fl_number": q.get("fl_number",""), "width": q.get("width"),
            "height": q.get("height"), "gusset": q.get("gusset",0),
            "substrate": q.get("substrate","Unknown"), "finish": q.get("finish","Unknown"),
            "seal_type": q.get("seal_type","Unknown"), "zipper": q.get("zipper","None"),
            "quantity": p.get("quantity"), "unit_price": p.get("unit_price"),
            "total_price": p.get("total_price"), "created_at": q.get("created_at",""),
        })
    print(f"  Joined rows: {len(rows)}")

    print("\n── Deduplication ──")
    groups = defaultdict(list)
    for r in rows:
        key = (r["fl_number"], r.get("width"), r.get("height"),
               r.get("gusset"), r.get("substrate"), r.get("quantity"))
        groups[key].append(r)
    deduped = [sorted(g, key=lambda x: x.get("created_at",""), reverse=True)[0] for g in groups.values()]
    print(f"  Before: {len(rows)}  After: {len(deduped)}")

    print("\n── Computing Known Costs ──")
    results = []; skipped = errors = 0
    for r in deduped:
        try:
            w = float(r.get("width") or 0); h = float(r.get("height") or 0)
            g = float(r.get("gusset") or 0); qty = int(float(r.get("quantity") or 0))
            up = float(r.get("unit_price") or 0)
            if w<=0 or h<=0 or qty<=0 or up<=0 or up<0.01 or up>10.0: skipped+=1; continue
            z = r.get("zipper","None")
            hz = z is not None and str(z).lower() not in ("none","","nan")
            kn = calculate_ross_known_cost(w, h, g, qty, hz)
            if kn is None: errors+=1; continue
            res = up - kn["known_unit"]
            results.append({
                "fl_number": r.get("fl_number",""), "width": w, "height": h, "gusset": g,
                "substrate": r.get("substrate","Unknown"), "finish": r.get("finish","Unknown"),
                "seal_type": r.get("seal_type","Unknown"), "zipper": z,
                "quantity": qty, "unit_price": up,
                "known_unit_cost": kn["known_unit"], "residual": res,
                "residual_pct": res/up*100 if up>0 else 0,
                "known_pct": kn["known_unit"]/up*100 if up>0 else 0,
                "click_cost_per_unit": kn["click_cost"]/qty,
                "priming_per_unit": kn["priming_cost"]/qty,
                "hp_labor_per_unit": (kn["hp_makeready"]+kn["hp_run_cost"])/qty,
                "converting_per_unit": ROSS_CONVERTING_PER_POUCH,
                "zipper_per_unit": kn["zipper_cost"]/qty if qty>0 else 0,
                "no_across": kn["no_across"], "no_around": kn["no_around"],
                "stock_width": kn["stock_width"], "stock_length_ft": kn["stock_length_ft"],
                "labels_per_cycle": kn["labels_per_cycle"],
            })
        except: errors += 1
    print(f"  Valid: {len(results)}  Skipped: {skipped}  Errors: {errors}")
    if not results: print("No valid results!"); return

    # ═══ ANALYSIS ═══
    print("\n" + "=" * 70)
    print("RESIDUAL ANALYSIS — REAL ROSS DATA")
    print("=" * 70)
    res_vals = [r["residual"] for r in results]
    ups = [r["unit_price"] for r in results]
    kcs = [r["known_unit_cost"] for r in results]
    mp = sum(ups)/len(ups); mk = sum(kcs)/len(kcs); mr = sum(res_vals)/len(res_vals)

    print(f"\n  Total valid rows: {len(results)}")
    print(f"\n── Price & Cost Summary ──")
    print(f"  Mean quoted unit price:  ${mp:.4f}")
    print(f"  Mean known unit cost:    ${mk:.4f}")
    print(f"  Mean residual:           ${mr:.4f}")
    print(f"  Median residual:         ${sorted(res_vals)[len(res_vals)//2]:.4f}")

    kp = [r["known_pct"] for r in results]; rp = [r["residual_pct"] for r in results]
    print(f"\n── Cost Decomposition ──")
    print(f"  Known cost share:  {sum(kp)/len(kp):.1f}% of quoted price")
    print(f"  Residual share:    {sum(rp)/len(rp):.1f}% of quoted price")
    nc = sum(1 for r in res_vals if r < 0)
    print(f"\n  Negative residuals: {nc} ({nc/len(results)*100:.1f}%)")
    if nc > 0:
        nv = [r for r in res_vals if r < 0]
        print(f"  Mean negative:     ${sum(nv)/len(nv):.4f}")

    print(f"\n── Per-Unit Components ──")
    for c in ["click_cost_per_unit","priming_per_unit","hp_labor_per_unit","converting_per_unit","zipper_per_unit"]:
        v = sum(r[c] for r in results)/len(results)
        print(f"  {c:25s}  ${v:.4f}  ({v/mp*100:.1f}%)")
    print(f"  {'residual (material+margin)':25s}  ${mr:.4f}  ({mr/mp*100:.1f}%)")

    for dim, key in [("Substrate","substrate"),("Finish","finish"),("Quantity","quantity"),
                     ("Zipper","zipper"),("Seal Type","seal_type")]:
        print(f"\n── Residual by {dim} ──")
        if dim == "Quantity":
            for lbl,lo,hi in [("1K-4K",1000,4000),("4K-6K",4001,6000),("6K-10K",6001,10000),
                              ("10K-25K",10001,25000),("25K+",25001,999999999)]:
                ss = [r for r in results if lo<=r["quantity"]<=hi]
                if len(ss)>=3:
                    print(f"  {lbl:25s}  ${sum(r['residual'] for r in ss)/len(ss):.4f} "
                          f"({sum(r['residual_pct'] for r in ss)/len(ss):.1f}%)  N={len(ss)}")
        else:
            for val in sorted(set(str(r[key]) for r in results)):
                ss = [r for r in results if str(r[key])==val]
                if len(ss)>=3:
                    neg = sum(1 for r in ss if r["residual"]<0)
                    print(f"  {val:25s}  ${sum(r['residual'] for r in ss)/len(ss):.4f} "
                          f"({sum(r['residual_pct'] for r in ss)/len(ss):.1f}%)  Neg:{neg}/{len(ss)}  N={len(ss)}")

    print(f"\n── Layout Distribution ──")
    ac = {}
    for r in results: ac[r["no_across"]] = ac.get(r["no_across"],0)+1
    for na,cnt in sorted(ac.items()):
        print(f"  no_across={na}:  {cnt} ({cnt/len(results)*100:.1f}%)")
    print(f"  Stock widths: {sorted(set(round(r['stock_width'],1) for r in results))}")

    # ═══ ML COMPARISON ═══
    if len(results) >= 30:
        print("\n" + "=" * 70)
        print("SEMI-DETERMINISTIC vs PURE ML — 5-FOLD CV")
        print("=" * 70)
        df = pd.DataFrame(results)
        df["bag_area_sqin"] = df["width"]*df["height"]
        df["print_width"] = df["height"]*2+df["gusset"]
        df["print_area_msi"] = df["print_width"]*df["height"]/1000
        df["log_quantity"] = np.log10(df["quantity"].clip(lower=1))
        df["inv_quantity"] = 1.0/df["quantity"].clip(lower=1)
        df["area_x_logqty"] = df["bag_area_sqin"]*df["log_quantity"]
        df["has_gusset"] = (df["gusset"]>0).astype(int)
        df["has_zipper_num"] = df["zipper"].apply(lambda z: 0 if (z is None or str(z).lower() in ("none","","nan")) else 1)
        df["zipper_width_interaction"] = df["width"]*df["has_zipper_num"]
        df["ross_converting_cost"] = df.apply(lambda r: 0.055+(5.258772*r["width"]*0.95/1000 if r["has_zipper_num"] else 0), axis=1)
        nf = ["width","height","gusset","bag_area_sqin","print_width","print_area_msi",
              "quantity","log_quantity","inv_quantity","area_x_logqty","has_gusset",
              "has_zipper_num","zipper_width_interaction","ross_converting_cost"]
        cf = ["substrate","finish","seal_type","zipper"]
        af = nf + cf
        enc = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        df[cf] = enc.fit_transform(df[cf].fillna("Unknown"))
        df[nf] = df[nf].fillna(0).astype(float)
        X = df[af].values; yp = df["unit_price"].values; yr = df["residual"].values; ka = df["known_unit_cost"].values
        vs = yr > 0
        print(f"\n  Total: {len(df)}  Positive residual: {vs.sum()} ({vs.mean()*100:.1f}%)")
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        sm, pm = [], []
        last_semi = None
        for fold, (tri, tei) in enumerate(kf.split(X)):
            Xtr,Xte = X[tri],X[tei]; yptr,ypte = yp[tri],yp[tei]
            yrtr = yr[tri]; kte = ka[tei]
            tv = yptr>0; tev = ypte>0
            if tv.sum()<10 or tev.sum()<5: continue
            mp_ = GradientBoostingRegressor(n_estimators=500,max_depth=6,learning_rate=0.02,
                min_samples_leaf=3,subsample=0.8,loss="huber",random_state=42)
            mp_.fit(Xtr[tv], np.log(yptr[tv]))
            pp = np.exp(mp_.predict(Xte[tev]))
            pmape = np.mean(np.abs(pp-ypte[tev])/ypte[tev])*100; pm.append(pmape)
            tp = yrtr>0
            if tp.sum()<10: sm.append(pmape); continue
            ms = GradientBoostingRegressor(n_estimators=500,max_depth=5,learning_rate=0.02,
                min_samples_leaf=5,subsample=0.8,loss="huber",random_state=42)
            ms.fit(Xtr[tp], np.log(yrtr[tp]))
            pr = np.exp(ms.predict(Xte[tev]))
            ps = kte[tev]+pr
            smape = np.mean(np.abs(ps-ypte[tev])/ypte[tev])*100; sm.append(smape)
            last_semi = ms
            print(f"  Fold {fold+1}: Semi-det={smape:.1f}%  Pure ML={pmape:.1f}%")
        if sm and pm:
            print(f"\n  {'Approach':<30s}  {'MAPE':>8s}  {'Std':>8s}")
            print(f"  {'-'*50}")
            print(f"  {'Semi-Deterministic':<30s}  {np.mean(sm):>7.1f}%  {np.std(sm):>7.1f}%")
            print(f"  {'Pure ML (current)':<30s}  {np.mean(pm):>7.1f}%  {np.std(pm):>7.1f}%")
            imp = np.mean(pm)-np.mean(sm)
            if imp>0: print(f"\n  ✓ Semi-deterministic is {imp:.1f}pp better!")
            else: print(f"\n  ✗ Pure ML is {-imp:.1f}pp better")
        if last_semi is not None:
            print(f"\n── Feature Importance (Residual Model) ──")
            for f,i in sorted(zip(af, last_semi.feature_importances_), key=lambda x:x[1], reverse=True)[:12]:
                print(f"  {f:30s}  {i:.4f}")

    out = "ross_residual_analysis_real.csv"
    with open(out,"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys())); w.writeheader(); w.writerows(results)
    print(f"\n  Saved: {out}")

    print(f"\n── Worst 10 Negative Residuals ──")
    for r in sorted([r for r in results if r["residual"]<0], key=lambda r:r["residual"])[:10]:
        print(f"  {r['fl_number']:15s} {r['width']}W×{r['height']}H×{r['gusset']}G  "
              f"qty={r['quantity']:>6,}  actual=${r['unit_price']:.4f}  known=${r['known_unit_cost']:.4f}  "
              f"res=${r['residual']:.4f}  ({r['substrate']}, {r['zipper']})")
    print(f"\n── Worst 10 Positive Residuals ──")
    for r in sorted(results, key=lambda r:r["residual"], reverse=True)[:10]:
        print(f"  {r['fl_number']:15s} {r['width']}W×{r['height']}H×{r['gusset']}G  "
              f"qty={r['quantity']:>6,}  actual=${r['unit_price']:.4f}  known=${r['known_unit_cost']:.4f}  "
              f"res=${r['residual']:.4f}  ({r['substrate']}, {r['zipper']})")

if __name__ == "__main__":
    run()
