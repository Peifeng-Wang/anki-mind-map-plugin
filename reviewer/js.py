"""JavaScript template generation for the review indicator."""
import json


INDICATOR_ID = "mindmap-indicator"
CLEAR_INDICATOR_JS = f"""
(function() {{
    var existing = document.getElementById('{INDICATOR_ID}');
    if (existing) {{
        existing.remove();
    }}
}})();
"""


def _build_indicator_js(mindmap_title, pycmd_param):
    """Build JavaScript that replaces the review indicator."""
    display_title = (mindmap_title or "").replace("\n", " ")
    safe_title = json.dumps(display_title)
    safe_pycmd = json.dumps(pycmd_param or "")

    return f"""
(function() {{
    // Remove existing indicator
    var existing = document.getElementById('{INDICATOR_ID}');
    if (existing) {{
        existing.remove();
    }}

    // Only add if there's a mind map
    if ({safe_title} === "") {{
        return;
    }}

    var indicator = document.createElement('div');
    indicator.id = '{INDICATOR_ID}';
    indicator.style.cssText = 'position:fixed;top:10px;right:10px;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:8px 15px;border-radius:20px;font-size:13px;font-weight:500;box-shadow:0 2px 10px rgba(0,0,0,0.2);cursor:pointer;z-index:10000;display:flex;align-items:center;gap:6px;transition:all 0.3s ease;user-select:none;';
    indicator.title = 'Click to open mind map';
    indicator.onclick = function() {{ pycmd({safe_pycmd}); }};
    indicator.onmouseover = function() {{ this.style.transform='scale(1.05)';this.style.boxShadow='0 4px 15px rgba(0,0,0,0.3)'; }};
    indicator.onmouseout = function() {{ this.style.transform='scale(1)';this.style.boxShadow='0 2px 10px rgba(0,0,0,0.2)'; }};

    var svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('width','16');
    svg.setAttribute('height','16');
    svg.setAttribute('viewBox','0 0 24 24');
    svg.setAttribute('fill','none');
    svg.setAttribute('stroke','currentColor');
    svg.setAttribute('stroke-width','2');

    [[12,12,3],[5,7,2],[19,7,2],[5,17,2],[19,17,2]].forEach(function(c){{
        var circle=document.createElementNS('http://www.w3.org/2000/svg','circle');
        circle.setAttribute('cx',c[0]);circle.setAttribute('cy',c[1]);circle.setAttribute('r',c[2]);
        svg.appendChild(circle);
    }});

    ['M9.5 10.5L7 8','M14.5 10.5L17 8','M9.5 13.5L7 16','M14.5 13.5L17 16'].forEach(function(d){{
        var path=document.createElementNS('http://www.w3.org/2000/svg','path');
        path.setAttribute('d',d);
        svg.appendChild(path);
    }});

    indicator.appendChild(svg);

    var span=document.createElement('span');
    span.style.cssText='max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
    span.textContent={safe_title};
    indicator.appendChild(span);

    document.body.appendChild(indicator);
}})();
"""
