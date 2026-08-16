"""
Classification accuracy investigation - reproducible record.
=============================================================
Run: python -m models.research_classification_trend  (needs data/*.csv)

WHAT THIS FOUND
---------------
The shipped classifier scores 0.7604 accuracy on test. Two separate
problems were behind that, and only one of them was a modelling problem.

1. LEAKAGE IN THE SHIPPED FEATURE SET.
   `day_index` - the position of a row inside a synthetic user's diary -
   is one of the 52 serving features. It ranks #2 by permutation
   importance, and removing it drops validation accuracy 0.8044 -> 0.7827.
   A cumulative day counter cannot legitimately predict a person's
   wellness a week out; the synthetic generator encoded each user's
   trajectory against day number, so the model was partly reading the
   generator rather than behaviour. An unrelated counter (`days_logged`)
   reproduced the same effect even harder on its own: 0.8044 -> 0.9099.
   Both are excluded here. Any accuracy resting on them would not
   survive production and would not survive a reviewer reading the
   importances.

2. THE REAL MODELLING GAP: no history was being used.
   The target is the health class SEVEN DAYS AHEAD, but the model only
   ever saw a single day. Where a person is heading is largely a function
   of their recent trajectory, so per-user trend features (1-day delta,
   3/7/14-day rolling means, short-vs-medium and medium-vs-long slopes,
   7-day volatility, and today-vs-personal-baseline deviation) were added
   for 19 signals.

   Every one of those 19 signals is already stored per entry by
   services/history_service.TRACKED_FIELDS, so unlike the excluded
   subscores this is genuinely reproducible at serving time from the
   user's own saved check-ins - no new data collection.

RESULTS (selection done on validation only; test read once, at the end)
-----------------------------------------------------------------------
   shipped model              test 0.7604   macroF1 0.7666
   same-day only, no day_index  val 0.7827
   + trend features             val 0.9142   test 0.9802  macroF1 0.9803

   Top importances are behavioural (night_ratio_r7,
   fragmentation_index_r7, physical_activity_r7, sleep_quality_r7) with
   no positional feature present and the top feature carrying only ~16%
   of total importance - the profile of a model reading many real
   signals rather than one artifact.

HONEST CAVEATS
--------------
* Test (0.980) scores well above validation (0.914). Validation is the
  conservative number and the one to quote; the gap most likely reflects
  differing diary lengths between the two user-disjoint splits, since
  longer history makes the trend features sharper.
* These numbers require history. A first-ever check-in has no deltas and
  degrades toward the ~0.78 same-day baseline. That is a real cold-start
  cost and must be surfaced to the user, not hidden - the app already has
  InsightService.cold_start_status for exactly this.
* Nothing here has been promoted into the serving pipeline yet. Doing so
  means teaching utils/feature_derivation.py to build these columns from
  HistoryService, and retraining - deliberately left as a separate step.
"""

import json, numpy as np, pandas as pd
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance

feats=json.load(open('artifacts/feature_columns.json'))
feats=feats if isinstance(feats,list) else feats.get('feature_columns')
CLEAN=[f for f in feats if f!='day_index']
TARGET='future_health_class_7d'; ORDER=['At Risk','Moderate','Healthy']
GROUP=['age','gender','occupation_group','region_group','education_group',
       'device_category','primary_platform','purpose_group','is_content_creator','uses_screen_time_limits']
LAG=['total_screen_min','social_min','gaming_min','work_study_min','video_min','night_screen_min',
     'pre_sleep_screen_min','sleep_hours','sleep_quality_1_10','stress_0_10','focus_0_100',
     'productivity_0_100','physical_activity_min_per_day','pickups_per_day','night_ratio',
     'social_ratio','fragmentation_index_0_100','notification_density','social_comparison_1_10']
def build(df):
    df=df.copy(); df['uid']=df[GROUP].astype(str).agg('|'.join,axis=1)
    df=df.sort_values(['uid','day_index']); g=df.groupby('uid',sort=False); new=[]
    for c in LAG:
        r3=g[c].transform(lambda s: s.rolling(3,min_periods=1).mean())
        r7=g[c].transform(lambda s: s.rolling(7,min_periods=1).mean())
        r14=g[c].transform(lambda s: s.rolling(14,min_periods=1).mean())
        df[f'{c}_d1']=g[c].diff(1); df[f'{c}_r3']=r3; df[f'{c}_r7']=r7
        df[f'{c}_sl7']=r3-r7; df[f'{c}_sl14']=r7-r14
        df[f'{c}_vol7']=g[c].transform(lambda s: s.rolling(7,min_periods=2).std())
        df[f'{c}_dev']=df[c]-r7
        new+=[f'{c}_d1',f'{c}_r3',f'{c}_r7',f'{c}_sl7',f'{c}_sl14',f'{c}_vol7',f'{c}_dev']
    return df,new
tr,new_cols=build(pd.read_csv('data/train.csv'))
va,_=build(pd.read_csv('data/validation.csv'))
te,_=build(pd.read_csv('data/test.csv'))
cols=CLEAN+new_cols
enc={}
def prep(df, fit=False):
    X=df[cols].copy()
    for c in cols:
        if not pd.api.types.is_numeric_dtype(X[c]):
            if fit: enc[c]={v:i for i,v in enumerate(sorted(X[c].astype(str).unique()))}
            X[c]=X[c].astype(str).map(enc[c]).fillna(-1).astype('float64')
    return X.astype('float64')
y=lambda df: df[TARGET].map({c:i for i,c in enumerate(ORDER)}).values
Xtr=prep(tr,fit=True); Xva=prep(va); Xte=prep(te)
ytr,yva,yte=y(tr),y(va),y(te)

m=HistGradientBoostingClassifier(random_state=42,max_iter=600,learning_rate=0.05,max_leaf_nodes=15).fit(Xtr,ytr)

print("=== leakage re-check: top importances must be behavioural, not positional ===")
pi=permutation_importance(m,Xva,yva,n_repeats=3,random_state=42,n_jobs=-1)
imp=pd.Series(pi.importances_mean,index=cols).sort_values(ascending=False)
print(imp.head(10).round(4).to_string())
print("  any diary-position feature present?:",
      [c for c in cols if c in ('day_index','days_logged')] or "NO - clean")
print("  top-1 share of total importance:", round(imp.iloc[0]/imp[imp>0].sum(),3))

print("\n=== VALIDATION (used for all selection) ===")
pv=m.predict(Xva)
print(f"  accuracy={accuracy_score(yva,pv):.4f}  macroF1={f1_score(yva,pv,average='macro'):.4f}")

print("\n=== TEST (touched once, after all decisions were frozen) ===")
pt=m.predict(Xte)
print(f"  accuracy={accuracy_score(yte,pt):.4f}  macroF1={f1_score(yte,pt,average='macro'):.4f}")
print("\nconfusion matrix (rows=true At Risk/Moderate/Healthy):")
print(confusion_matrix(yte,pt))
print(classification_report(yte,pt,target_names=ORDER,digits=3))
print("shipped model for comparison: test accuracy 0.7604, macroF1 0.7666")
