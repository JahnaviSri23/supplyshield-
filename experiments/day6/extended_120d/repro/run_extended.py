from pathlib import Path
import argparse, csv, datetime, hashlib, importlib, json, shutil, subprocess, sys, time
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent
REPO=PACKAGE.parents[2]
def sha(data): return hashlib.sha256(data).hexdigest()
def iso_now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--horizon",type=int,choices=(40,120),required=True)
    ap.add_argument("--waiting-rate",type=float,choices=(1.0,24.0),required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out).resolve()
    if out.exists(): raise SystemExit(f"refusing to overwrite output: {out}")
    root=HERE/"isolated"
    if not root.exists():
        subprocess.run([sys.executable,str(HERE/"prepare_isolated.py"),"--root",str(root)],cwd=REPO,check=True)
    sys.path.insert(0,str(root))
    sim=importlib.import_module("sim.simulator")
    sim_path=Path(sim.__file__).resolve()
    expected=json.loads((PACKAGE/"manifests"/"pinned_inputs_manifest.json").read_text(encoding="utf-8-sig"))["simulator_provenance"]["candidate_byte_sha256"]
    if not sim_path.is_relative_to(root) or sha(sim_path.read_bytes())!=expected: raise SystemExit("isolated simulator path/hash assertion failed")
    adapter=importlib.import_module("models.day6_integration")
    adapter_path=Path(adapter.__file__).resolve()
    expected_adapter=json.loads((PACKAGE/"manifests"/"pinned_inputs_manifest.json").read_text(encoding="utf-8-sig"))["isolated_root_file_sha256"]["models/day6_integration.py"]
    if not adapter_path.is_relative_to(root) or sha(adapter_path.read_bytes())!=expected_adapter and sha(adapter_path.read_bytes().replace(b"\r\n",b"\n").replace(b"\r",b"\n"))!=expected_adapter:
        raise SystemExit("isolated adapter path/hash assertion failed")
    original=sim.simulate;calls=[]
    names=["do nothing","greedy","preserve (affected flows only)","LP (all flows)"]
    def wrapped(graph,scenario,plan=None):
        index=len(calls);before=dict(scenario);changed=dict(before);changed["horizon"]=args.horizon
        graph.graph["waiting_cost"]=args.waiting_rate
        result=original(graph,changed,plan=plan);hist=result.get("history",[])
        calls.append({"scenario_id":before.get("id"),"strategy":names[index%4],"horizon_passed":args.horizon,"waiting_rate":args.waiting_rate,"simulator_reported_days_run":len(hist),"last_history_day":hist[-1].get("day") if hist else None,"other_scenario_keys_unchanged":all(before[k]==changed[k] for k in before if k!="horizon")})
        return result
    adapter.simulate=wrapped
    started=iso_now();tick=time.perf_counter()
    adapter_out=root/"runner_outputs"/out.name
    result=adapter.run_real_integration(root=root,output_dir=adapter_out)
    runtime=time.perf_counter()-tick;ended=iso_now()
    out.mkdir(parents=True)
    for filename in ("scenario_strategy_summary.csv","execution_manifest.json"):
        shutil.copyfile(adapter_out/filename,out/filename)
    runtime=time.perf_counter()-tick;ended=iso_now()
    if len(calls)!=40 or any(not x["other_scenario_keys_unchanged"] for x in calls): raise SystemExit("call assertions failed")
    raw=out/"scenario_strategy_summary.csv";corrected=out/"scenario_strategy_summary_corrected.csv"
    with raw.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f));fields=list(rows[0])
    for row in rows: row["simulator_horizon_days"]=str(args.horizon)
    with corrected.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    manifest={"status":"MEASURED_PROVISIONAL","started_utc":started,"ended_utc":ended,"runtime_seconds":runtime,"configuration":{"horizon":args.horizon,"waiting_rate":args.waiting_rate,"demand_days":14,"closure_days":14,"unmet_penalty":96.0},"simulator":{"path_within_isolated_root":sim_path.relative_to(root).as_posix(),"sha256_crlf":sha(sim_path.read_bytes()),"calls":40},"adapter":{"path_within_isolated_root":adapter_path.relative_to(root).as_posix(),"sha256":sha(adapter_path.read_bytes())},"per_call":calls,"adapter_summary_sha256":sha(raw.read_bytes()),"corrected_summary_sha256":sha(corrected.read_bytes()),"wrapper_sha256_crlf":sha(Path(__file__).read_bytes())}
    (out/"measured_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"out":str(out),"horizon":args.horizon,"waiting_rate":args.waiting_rate,"calls":len(calls),"runtime_seconds":runtime,"corrected_summary_sha256":manifest["corrected_summary_sha256"]},indent=2))
if __name__=="__main__": main()
