#!/usr/bin/env python3
"""Draw the independently derived four-Fe input patterns, with periodic images.

Inputs: the actual FE_XY and PATTERNS definitions in fese.py; no fitted data.
Outputs: figures/input_magnetic_patterns.png and .svg plus a hash manifest.
Dependencies: Python >=3.10, NumPy and Matplotlib. Example: python draw_magnetic_cell.py
The arrows denote input signs along a common spin axis; they are not measured
moments or spin-orbit-selected spatial directions. Final states come from logs.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import fese

ROOT=Path(__file__).resolve().parent


def main():
    """Render a periodic Fe-plane schematic in nearest-neighbor coordinate units."""
    out=ROOT/'figures';out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(10.8,4),constrained_layout=True)
    for ax,state in zip(axes,('FM','CB','STRIPE')):
        signs=fese.PATTERNS[state]
        for i in range(-1,3):
            for j in range(-1,3):
                index=(i%2)+2*(j%2)
                sign=signs[index]
                central=i in (0,1) and j in (0,1)
                color=('#b45335' if sign>0 else '#2563a6')
                if i<2:ax.plot([i,i+1],[j,j],color='#cbd5e1',lw=.7,zorder=0)
                if j<2:ax.plot([i,i],[j,j+1],color='#cbd5e1',lw=.7,zorder=0)
                ax.scatter([i],[j],s=100 if central else 40,color=color,alpha=1 if central else .28,zorder=2)
                arrow=ax.annotate('',xy=(i,j+.22*sign),xytext=(i,j-.22*sign),
                            arrowprops={'arrowstyle':'-|>','color':color,'lw':2 if central else 1,'alpha':1 if central else .28})
                arrow.arrow_patch.set_clip_path(ax.patch)
                if central:ax.text(i+.12,j+.12,f'Fe{index+1}',fontsize=8)
        # This translated repeat boundary encloses exactly the four displayed Fe.
        ax.add_patch(Rectangle((-.45,-.45),2,2,fill=False,ls='--',lw=1.2,color='#334155'))
        ax.set(xlim=(-.8,2.35),ylim=(-.8,2.35),aspect='equal',xlabel='Along A/2',ylabel='Along B/2')
        ax.set_title(state+' input',loc='left',weight='bold')
        ax.set_xticks([0,1,2]);ax.set_yticks([0,1,2])
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Four-Fe magnetic repeat: initial signs, with faded periodic images',fontsize=12,weight='bold')
    paths=[out/'input_magnetic_patterns.png',out/'input_magnetic_patterns.svg']
    fig.savefig(paths[0],dpi=180,bbox_inches='tight');fig.savefig(paths[1],bbox_inches='tight');plt.close(fig)
    fese.dump(out/'input_magnetic_patterns_manifest.json',{
        'purpose':'Input geometry and signs only; not final-state evidence',
        'source_sha256':fese.sha(__file__),'geometry_source_sha256':fese.sha(Path(fese.__file__)),
        'coordinate_definition':'A=a(1,1,0), B=a(-1,1,0); displayed unit lengths |A|/2=|B|/2=a/sqrt(2)',
        'patterns':{x:fese.PATTERNS[x] for x in ('FM','CB','STRIPE')},
        'artifacts':[{'path':str(p.relative_to(ROOT)),'sha256':fese.sha(p),'bytes':p.stat().st_size} for p in paths]})
    print('Rendered the three declared input patterns; no scientific outcomes inferred')


if __name__=='__main__':main()
