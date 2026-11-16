"""Generate prespecified, disjoint-subject perturbations only after policy freeze."""
import hashlib
import numpy as np
import pandas as pd

def generate(source,seed,held_out=False):
    rng=np.random.default_rng(seed);dirty={k:v.copy(deep=True) for k,v in source.items()}
    used=set();truth=[];coverage=[];quota=12 if held_out else 8
    pool={s for s in source["dm"].USUBJID
          if int(hashlib.sha256((s+"|scope-v1").encode()).hexdigest(),16)%2==int(held_out)}
    def inject(domain,field,label,critical,eligible,change):
        frame=source[domain]
        indices=[i for i in frame.index[eligible & frame.USUBJID.isin(pool)] if (domain,int(i)) not in used]
        selected=rng.choice(indices,size=min(quota,len(indices)),replace=False)
        if not len(selected):raise ValueError("No eligible source records for "+label)
        for i in selected:
            i=int(i);old=frame.at[i,field];new=change(frame.loc[i])
            if (pd.isna(old) and pd.isna(new)) or (pd.notna(old) and pd.notna(new) and old==new):
                raise ValueError("No-op perturbation: "+label)
            dirty[domain].at[i,field]=new;used.add((domain,i))
            truth.append({"mutationId":f"{seed}-{len(truth)+1:03}","domain":domain.upper(),
                "sourceRow":i,"subject":frame.at[i,"USUBJID"],"field":field,"family":label,
                "critical":critical,"before":old.item() if isinstance(old,np.generic) else old,
                "after":new.item() if isinstance(new,np.generic) else new})
        coverage.append({"family":label,"critical":critical,"requested":quota,"injected":len(selected)})
    dm=source["dm"];randomized=dm.ARMCD.ne("") & dm.ARMCD.ne("Scrnfail")
    inject("dm","ARMCD","Planned arm code",True,randomized,lambda r:"" if held_out else "INVALID_ARM")
    inject("dm","ACTARMCD","Actual arm code",True,randomized,lambda r:"INVALID_ACTUAL_ARM")
    q=source["qs"]
    baseline=q.QSBLFL.eq("Y") & q.QSTESTCD.isin(["ACITM01","ACITM02","ACITM04","ACITM05","ACITM06","ACITM07","ACITM08","ACITM11","ACITM12","ACITM13","ACITM14"])
    inject("qs","QSDTC","Baseline assessment date",True,baseline & q.QSDTC.str.len().ge(10),
        lambda r:(pd.Timestamp(r.QSDTC[:10])+pd.Timedelta(days=60 if held_out else 21)).strftime("%Y-%m-%d"))
    inject("qs","QSSTRESN","Baseline ADAS item score",True,baseline & q.QSSTRESN.notna(),
        lambda r:float("nan") if held_out else 99.)
    ds=source["ds"];post=ds.DSCAT.eq("DISPOSITION EVENT") & ds.VISITNUM.gt(3)
    inject("ds","DSDECOD","Disposition code",True,post,lambda r:"UNRECOGNIZED DISPOSITION")
    starts=dm.set_index("USUBJID").RFSTDTC
    inject("ds","DSSTDTC","Disposition date",True,post & ds.USUBJID.map(starts).str.len().ge(10),
        lambda r:(pd.Timestamp(starts[r.USUBJID][:10])-pd.Timedelta(days=30 if held_out else 3)).strftime("%Y-%m-%d"))
    ae=source["ae"]
    inject("ae","AESTDTC","AE onset before exposure",True,ae.AESTDTC.str.len().ge(10)&ae.USUBJID.map(starts).str.len().ge(10),
        lambda r:(pd.Timestamp(starts[r.USUBJID][:10])-pd.Timedelta(days=30 if held_out else 7)).strftime("%Y-%m-%d"))
    ex=source["ex"]
    inject("ex","EXSTDTC","Exposure interval reversed",True,ex.EXENDTC.str.len().ge(10),
        lambda r:(pd.Timestamp(r.EXENDTC[:10])+pd.Timedelta(days=14 if held_out else 3)).strftime("%Y-%m-%d"))
    lb=source["lb"]
    inject("lb","LBSTRESN","Marked hepatic abnormality",True,lb.LBTESTCD.isin(["ALT","AST"])&lb.LBSTNRHI.gt(0)&lb.VISITNUM.isin([4,5,7,8,9,10,11,12]),
        lambda r:float(r.LBSTNRHI)*(15 if held_out else 8))
    vs=source["vs"]
    inject("vs","VSDTC","Vital clock metadata",False,vs.VSDTC.str.len().ge(10),
        lambda r:r.VSDTC[:10] if len(r.VSDTC)>10 else r.VSDTC+("T23:59" if held_out else "T12:34"))
    inject("vs","VSLOC","Vital location metadata",False,vs.VSLOC.str.strip().ne(""),lambda r:"")
    inject("vs","VSPOS","Vital position metadata",False,vs.VSPOS.str.strip().ne(""),lambda r:"")
    mh=source["mh"]
    inject("mh","MHSTDTC","Historical partial date",False,mh.MHCAT.eq("HISTORICAL DIAGNOSIS")&mh.MHSTDTC.str.len().ge(10),
        lambda r:r.MHSTDTC[:4 if held_out else 7])
    cm=source["cm"];otc=cm.CMTRT.str.contains("ASPIRIN|TYLENOL|VITAMIN|CENTRUM|CALCIUM",case=False,regex=True)
    inject("cm","CMROUTE","Routine OTC route",False,otc & cm.CMROUTE.str.strip().ne(""),lambda r:"")
    inject("cm","CMDOSE","Routine OTC dose",False,otc & cm.CMDOSE.notna(),lambda r:float("nan"))
    sc=source["sc"]
    inject("sc","SCCAT","SC category text",False,sc.SCCAT.str.strip().ne(""),lambda r:r.SCCAT.lower())
    return dirty,truth,coverage
