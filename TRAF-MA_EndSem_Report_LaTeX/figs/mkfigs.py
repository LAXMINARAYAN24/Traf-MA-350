"""Test helpers for mkfigs."""

import json, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
plt.rcParams.update({"font.size":9,"font.family":"serif","axes.spines.top":False,"axes.spines.right":False})
navy="#1F3864"; blue="#9DC3E6"; grey="#A6A6A6"; green="#70AD47"; amber="#FFC000"; red="#C0504D"

# ---- Fig: main comparison (full-v2, run-level, 5 seeds, bootstrap CI) ----
M=["Signal-aware\nRidge","Central\nGRU","Flat FedAvg\n(natural)","Flat FedAvg\n(IID ctrl.)","Hier. FedAvg\n(RSU self-upd. on)","Hier. FedAvg\n(RSU self-upd. off)"]
mae=[29.1487,29.6892,61.7315,60.0319,45.0405,61.3314]; mae_ci=[(25.6708,32.4885),(26.1924,33.1270),(59.5552,63.8186),(58.0437,61.9253),(41.1465,48.7605),(59.1904,63.3396)]
f1=[0.4191,0.4890,0.1490,0.1611,0.2867,0.1546]; f1_ci=[(0.3979,0.4402),(0.4573,0.5193),(0.1348,0.1625),(0.1348,0.1872),(0.2705,0.3027),(0.1404,0.1678)]
cols=[grey,navy,"#C55A11","#ED7D31",green,"#A9D18E"]
fig,ax=plt.subplots(1,2,figsize=(7.4,3.2))
for a,v,cis,t,yl in [(ax[0],mae,mae_ci,"Queue MAE at $t{+}30$ s (lower is better)","MAE (m)"),(ax[1],f1,f1_ci,"Congestion macro-F1 (higher is better)","Macro-F1")]:
    x=np.arange(6); lo=[v[i]-cis[i][0] for i in range(6)]; hi=[cis[i][1]-v[i] for i in range(6)]
    a.bar(x,v,color=cols,edgecolor="black",linewidth=0.4,yerr=[lo,hi],capsize=3,error_kw={"linewidth":0.8})
    a.set_xticks(x); a.set_xticklabels(M,fontsize=5.8); a.set_ylabel(yl); a.set_title(t,fontsize=8.5)
    a.grid(axis="y",alpha=0.3)
plt.tight_layout(); plt.savefig("figs/main_results.pdf"); plt.close()

# ---- Fig: class histograms per split / client type ----
H={"train / RSU":[163078,53682,58760],"val / RSU":[83134,26003,28623],"test / RSU":[82088,26471,29201],
   "train / vehicle":[792575,294898,1037692],"val / vehicle":[389562,141568,493587],"test / vehicle":[392184,143696,513845]}
fig,ax=plt.subplots(figsize=(6.4,2.8)); labs=list(H); 
tot=[sum(H[k]) for k in labs]; left=np.zeros(6)
for i,(nm,c) in enumerate([("free",green),("moderate",amber),("heavy",red)]):
    vals=np.array([H[k][i]/tot[j]*100 for j,k in enumerate(labs)])
    ax.barh(labs,vals,left=left,color=c,edgecolor="black",linewidth=0.4,label=nm)
    for j,v in enumerate(vals): ax.text(left[j]+v/2,j,f"{v:.0f}%",ha="center",va="center",fontsize=7)
    left+=vals
ax.invert_yaxis(); ax.set_xlabel("share of overlapping windows (%)"); ax.legend(ncol=3,loc="upper center",bbox_to_anchor=(0.5,1.18),frameon=False,fontsize=8)
plt.tight_layout(); plt.savefig("figs/class_dist.pdf"); plt.close()

# ---- Fig: scenario ladder ----
S=json.load(open("scen.json")); order=["free","light_moderate","moderate","moderate_heavy","heavy","single_arm","asymmetric","asymmetric_ew"]
lab=["free","light\nmoderate","moderate","moderate\nheavy","heavy","single\narm","asym.\nN/S","asym.\nE/W"]
arr=[S[k]["arr"] for k in order]; unf=[S[k]["unf"] for k in order]
fig,ax=plt.subplots(figsize=(6.4,2.8)); x=np.arange(8)
ax.bar(x,arr,color=blue,edgecolor="black",linewidth=0.4,label="arrived within 900 s")
ax.bar(x,unf,bottom=arr,color=red,edgecolor="black",linewidth=0.4,label="still in network at 900 s")
ax.set_xticks(x); ax.set_xticklabels(lab,fontsize=7); ax.set_ylabel("vehicles per run (mean of 20)"); ax.legend(frameon=False,fontsize=8); ax.grid(axis="y",alpha=0.3)
plt.tight_layout(); plt.savefig("figs/scenario_ladder.pdf"); plt.close()

# ---- Fig: central GRU per-seed ----
seeds=["20261031","20261032","20261033","20261034","20261035"]
mae_s=[28.2207,29.8459,29.0011,29.2135,32.1649]; f1_s=[0.5487,0.5895,0.6041,0.5668,0.6008]
fig,ax=plt.subplots(1,2,figsize=(6.6,2.5))
ax[0].bar(range(5),mae_s,color=navy,edgecolor="black",linewidth=0.4); ax[0].set_ylim(20,34); ax[0].set_ylabel("MAE (m)"); ax[0].set_title("Queue MAE",fontsize=8.5)
ax[1].bar(range(5),f1_s,color=navy,edgecolor="black",linewidth=0.4); ax[1].set_ylim(0.45,0.65); ax[1].set_ylabel("macro-F1"); ax[1].set_title("Congestion macro-F1",fontsize=8.5)
for a in ax: a.set_xticks(range(5)); a.set_xticklabels(["S1","S2","S3","S4","S5"]); a.set_xlabel("training seed (20261031 to 20261035)",fontsize=7.5); a.grid(axis="y",alpha=0.3)
plt.tight_layout(); plt.savefig("figs/central_seeds.pdf"); plt.close()
print("ok")
