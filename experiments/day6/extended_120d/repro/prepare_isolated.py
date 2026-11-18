from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, sys
HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
REPO = PACKAGE.parents[2]
MANIFEST = PACKAGE / "manifests" / "pinned_inputs_manifest.json"
def sha(data): return hashlib.sha256(data).hexdigest()
def lf(data): return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    args=parser.parse_args()
    root=Path(args.root).resolve()
    try: root.relative_to(PACKAGE.resolve())
    except ValueError: raise SystemExit("isolated root must stay inside extended_120d/repro")
    if root.exists(): raise SystemExit(f"refusing to overwrite existing isolated root: {root}")
    manifest=json.loads(MANIFEST.read_text(encoding="utf-8-sig"))
    expected=manifest["isolated_root_file_sha256"]
    sim_commit=manifest["simulator_provenance"]["candidate_commit"]
    git_bytes=subprocess.check_output(["git","show",f"{sim_commit}:sim/simulator.py"],cwd=REPO)
    lf_hash=sha(git_bytes)
    recorded_crlf=manifest["simulator_provenance"]["candidate_byte_sha256"]
    sim_bytes=git_bytes.replace(b"\n",b"\r\n")
    if sha(sim_bytes)!=recorded_crlf: raise SystemExit("pinned simulator CRLF hash mismatch")
    if sha(lf(git_bytes))!=lf_hash: raise SystemExit("pinned simulator LF normalization mismatch")
    paths=["models/day6_integration.py","models/test_day6_integration.py","opt/c_real_graph.py","opt/c_toy_recovery.py","models/outputs/risk_table.csv","experiments/c_multiflow_plans.json","data/processed/core_edges.csv","data/processed/core_nodes.csv","data/processed/core_train_legs.csv","data/processed/split_trip_ids.csv"]
    copy_bytes={}
    for rel in paths:
        if rel not in expected: raise SystemExit(f"manifest missing {rel}")
        candidates=[REPO/rel,PACKAGE/"work"/rel]
        src=None
        for candidate in candidates:
            if candidate.is_file():
                b=candidate.read_bytes()
                if sha(b)==expected[rel] or sha(lf(b))==expected[rel]: src=candidate;copy_bytes[rel]=b;break
        if src is None: raise SystemExit(f"no source matches manifest hash for {rel}")
    # Verify copied hashes from measured bytes before creating any files.
    for rel,b in copy_bytes.items():
        if sha(b)!=expected[rel] and sha(lf(b))!=expected[rel]: raise SystemExit(f"source hash mismatch: {rel}")
    root.mkdir(parents=True)
    (root/"sim").mkdir();(root/"sim/__init__.py").write_bytes(b"");(root/"sim/simulator.py").write_bytes(sim_bytes)
    for rel,b in copy_bytes.items():
        dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
    print(json.dumps({"root":str(root),"simulator_lf_sha256":lf_hash,"simulator_crlf_sha256":sha(sim_bytes),"files":{p:sha(b) for p,b in copy_bytes.items()}},indent=2))
if __name__=="__main__": main()
