"""Cache-only refresh: never fetch sources or execute paired challenges."""
import subprocess
from pathlib import Path
from validate_variants import main as variants
from dual_track import main as dual
from refresh_outputs import refresh_outputs

def main():
    from dual_track import OUT
    import json
    if (OUT/"scoped-study/scoped_results.json").exists():
        from export_scoped_study import export
        export(json.loads((OUT/"scoped-study/scoped_results.json").read_text()))
        return
    script=Path(__file__).with_name("validate_rebuild.py")
    result=subprocess.run(["python",str(script)],check=False)
    if result.returncode not in (0,2):
        raise RuntimeError("Clean audit failed to execute; abort output refresh")
    variants()
    dual()
    refresh_outputs()

if __name__=="__main__":main()
