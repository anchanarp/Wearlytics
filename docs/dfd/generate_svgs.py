#!/usr/bin/env python3
"""
Generate high quality vector SVG diagrams following the exact DFD notation from the reference screenshot:
- Entities: Rectangles with solid borders
- Processes: Ovals/Ellipses
- Data Stores: Open-ended rectangles with left divider [ | StoreName ]
- Data Flows: Directed arrows with clear action/data labels
"""

import os

OUTPUT_DIR = "/Users/anchana/Desktop/PROJECT/Wearlytics/docs/dfd"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Common SVG styles and defs
SVG_HEADER_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%" style="background:#ffffff; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <!-- Arrow marker -->
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#1e293b" />
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#2d6a4f" />
    </marker>
    <!-- Drop shadows for modern presentation -->
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="1" dy="2" stdDeviation="2" flood-color="#000000" flood-opacity="0.08"/>
    </filter>
  </defs>

  <!-- Academic Report Slide Accent Bars matching reference -->
  <rect x="40" y="25" width="220" height="7" fill="#2d6a4f" rx="2"/>
  <rect x="270" y="25" width="220" height="7" fill="#80b918" rx="2"/>
  <rect x="500" y="25" width="220" height="7" fill="#94a3b8" rx="2"/>

  <!-- Title -->
  <text x="40" y="65" font-size="19" font-weight="800" fill="#1e293b" letter-spacing="1">{title}</text>
  <text x="40" y="88" font-size="13" font-weight="500" fill="#64748b">{subtitle}</text>
"""

# Helper function to generate Data Store shape
def draw_data_store(x, y, w, h, name):
    # Open on the right, left vertical bar, vertical divider at x+25
    div_x = x + 25
    right_x = x + w
    bottom_y = y + h
    return f"""
    <!-- Data Store: {name} -->
    <g class="data-store">
      <!-- Background -->
      <path d="M {right_x} {y} L {x} {y} L {x} {bottom_y} L {right_x} {bottom_y}" fill="#ffffff" stroke="#1e293b" stroke-width="1.6"/>
      <!-- Vertical divider -->
      <line x1="{div_x}" y1="{y}" x2="{div_x}" y2="{bottom_y}" stroke="#1e293b" stroke-width="1.6"/>
      <!-- Label -->
      <text x="{div_x + (w - 25)/2}" y="{y + h/2 + 5}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">{name}</text>
    </g>
    """

# -------------------------------------------------------------
# 1. WEARLYTICS LEVEL 0 CONTEXT DIAGRAM
# -------------------------------------------------------------
def generate_wearlytics_level_0():
    w, h = 960, 600
    title = "LEVEL 0 CONTEXT DIAGRAM"
    subtitle = "Wearlytics — AI-Powered Digital Wardrobe & Outfit Recommendation System"

    content = SVG_HEADER_TEMPLATE.format(width=w, height=h, title=title, subtitle=subtitle)

    # Process: Center Oval (0.0 Wearlytics System)
    cx, cy, rx, ry = 480, 320, 115, 80
    content += f"""
    <!-- Process 0.0: Central System -->
    <g class="process">
      <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#ffffff" stroke="#1e293b" stroke-width="2" filter="url(#shadow)"/>
      <text x="{cx}" y="{cy - 12}" font-size="17" font-weight="700" fill="#0f172a" text-anchor="middle">Wearlytics</text>
      <text x="{cx}" y="{cy + 12}" font-size="16" font-weight="700" fill="#0f172a" text-anchor="middle">System</text>
      <text x="{cx}" y="{cy + 34}" font-size="12" font-weight="600" fill="#475569" text-anchor="middle">(0.0)</text>
    </g>
    """

    # Left Entity: User & Admin Requests
    ux, uy, uw, uh = 70, 245, 180, 150
    content += f"""
    <!-- Left Entity: Entities sending inputs -->
    <g class="entity">
      <rect x="{ux}" y="{uy}" width="{uw}" height="{uh}" fill="#ffffff" stroke="#1e293b" stroke-width="2" rx="4" filter="url(#shadow)"/>
      <text x="{ux + uw/2}" y="{uy + 40}" font-size="16" font-weight="700" fill="#0f172a" text-anchor="middle">User / Admin</text>
      <line x1="{ux + 20}" y1="{uy + 52}" x2="{ux + uw - 20}" y2="{uy + 52}" stroke="#cbd5e1" stroke-width="1.2"/>
      <text x="{ux + uw/2}" y="{uy + 75}" font-size="12" fill="#475569" text-anchor="middle">• Wardrobe Owner</text>
      <text x="{ux + uw/2}" y="{uy + 97}" font-size="12" fill="#475569" text-anchor="middle">• Fashion Client</text>
      <text x="{ux + uw/2}" y="{uy + 119}" font-size="12" fill="#475569" text-anchor="middle">• System Admin</text>
    </g>
    """

    # Right Entity: Entities receiving outputs (Matching screenshot dual-box convention)
    rx_e, ry_e, rw_e, rh_e = 710, 245, 180, 150
    content += f"""
    <!-- Right Entity: Entities receiving responses -->
    <g class="entity">
      <rect x="{rx_e}" y="{ry_e}" width="{rw_e}" height="{rh_e}" fill="#ffffff" stroke="#1e293b" stroke-width="2" rx="4" filter="url(#shadow)"/>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 40}" font-size="16" font-weight="700" fill="#0f172a" text-anchor="middle">User / Admin</text>
      <line x1="{rx_e + 20}" y1="{ry_e + 52}" x2="{rx_e + rw_e - 20}" y2="{ry_e + 52}" stroke="#cbd5e1" stroke-width="1.2"/>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 75}" font-size="12" fill="#475569" text-anchor="middle">• Wardrobe Owner</text>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 97}" font-size="12" fill="#475569" text-anchor="middle">• Fashion Client</text>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 119}" font-size="12" fill="#475569" text-anchor="middle">• System Admin</text>
    </g>
    """

    # Flows Left to Center
    # Flow 1: High-level request arrow (matching screenshot "request")
    content += f"""
    <!-- Request Arrow (User/Admin to System) -->
    <path d="M {ux + uw} 305 L {cx - rx - 8} 305" fill="none" stroke="#1e293b" stroke-width="1.8" marker-end="url(#arrow)"/>
    <rect x="290" y="285" width="65" height="20" fill="#ffffff"/>
    <text x="322" y="299" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">request</text>

    <!-- Specific Data Flow Details under arrow -->
    <text x="310" y="340" font-size="11" fill="#475569" text-anchor="middle">[ Credentials, Garment Details,</text>
    <text x="310" y="358" font-size="11" fill="#475569" text-anchor="middle">Styling Filters, Schedule, Feedback ]</text>
    """

    # Flows Center to Right
    # Flow 2: High-level response arrow (matching screenshot "response")
    content += f"""
    <!-- Response Arrow (System to User/Admin) -->
    <path d="M {cx + rx + 8} 305 L {rx_e - 2} 305" fill="none" stroke="#1e293b" stroke-width="1.8" marker-end="url(#arrow)"/>
    <rect x="615" y="285" width="75" height="20" fill="#ffffff"/>
    <text x="652" y="299" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">response</text>

    <!-- Specific Data Flow Details under arrow -->
    <text x="650" y="340" font-size="11" fill="#475569" text-anchor="middle">[ Auth Status, Wardrobe Catalog,</text>
    <text x="650" y="358" font-size="11" fill="#475569" text-anchor="middle">AI Outfits, Weekly Plan, Analytics ]</text>
    """

    content += "</svg>"
    with open(os.path.join(OUTPUT_DIR, "wearlytics_dfd_level_0.svg"), "w") as f:
        f.write(content)


# -------------------------------------------------------------
# 2. WEARLYTICS LEVEL 1 USER DFD
# -------------------------------------------------------------
def generate_wearlytics_level_1_user():
    w, h = 1000, 780
    title = "LEVEL 1 USER DFD"
    subtitle = "Decomposition of End-User Functional Flows in Wearlytics"

    content = SVG_HEADER_TEMPLATE.format(width=w, height=h, title=title, subtitle=subtitle)

    # 1. External Entity: User
    ux, uy, uw, uh = 40, 320, 110, 60
    content += f"""
    <!-- External Entity: User -->
    <g class="entity">
      <rect x="{ux}" y="{uy}" width="{uw}" height="{uh}" fill="#ffffff" stroke="#1e293b" stroke-width="2" rx="4" filter="url(#shadow)"/>
      <text x="{ux + uw/2}" y="{uy + 36}" font-size="15" font-weight="700" fill="#0f172a" text-anchor="middle">User</text>
    </g>
    """

    # 2. Process: Login
    lx, ly, lr_x, lr_y = 260, 350, 58, 42
    content += f"""
    <!-- Process: Login -->
    <g class="process">
      <ellipse cx="{lx}" cy="{ly}" rx="{lr_x}" ry="{lr_y}" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
      <text x="{lx}" y="{ly + 5}" font-size="14" font-weight="700" fill="#0f172a" text-anchor="middle">Login</text>
    </g>

    <!-- Arrow User -> Login -->
    <path d="M {ux + uw} 350 L {lx - lr_x - 4} 350" fill="none" stroke="#1e293b" stroke-width="1.6" marker-end="url(#arrow)"/>
    <text x="185" y="342" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">credentials</text>
    """

    # 3. Data Store: users (below Login)
    ds_login_x, ds_login_y, ds_login_w, ds_login_h = 190, 510, 140, 36
    content += draw_data_store(ds_login_x, ds_login_y, ds_login_w, ds_login_h, "users")

    # Arrows between Login and users Data Store (two arrows: username & password verification)
    content += f"""
    <!-- Login -> users (email/password query) -->
    <path d="M 235 390 L 235 506" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="175" y="440" width="55" height="16" fill="#ffffff"/>
    <text x="202" y="452" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">username</text>

    <!-- users -> Login (hash / auth token) -->
    <path d="M 285 506 L 285 392" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="290" y="440" width="55" height="16" fill="#ffffff"/>
    <text x="317" y="452" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">password</text>
    """

    # 4. User Sub-Processes (Fan out from Login via 'valid user')
    processes = [
        {"id": "p1", "name": "Manage\nWardrobe", "store": "clothing_items", "add": "add/wear details", "get": "get clothes details", "y": 140},
        {"id": "p2", "name": "AI Outfit\nGenerator", "store": "outfits", "add": "generate outfit", "get": "get outfit catalog", "y": 270},
        {"id": "p3", "name": "Weekly\nPlanner", "store": "weekly_plans", "add": "assign schedule", "get": "get weekly plan", "y": 400},
        {"id": "p4", "name": "Wardrobe\nAnalytics", "store": "clothing_items", "add": "log wear count", "get": "get utilization stats", "y": 530},
        {"id": "p5", "name": "Outfit\nFeedback", "store": "outfit_feedback", "add": "submit rating", "get": "get feedback data", "y": 660},
    ]

    proc_cx = 530
    store_x = 760
    store_w = 175
    store_h = 36

    for p in processes:
        py = p["y"]
        lines = p["name"].split("\n")
        
        # Draw Process Oval
        content += f"""
        <!-- Process: {p['name'].replace(chr(10), ' ')} -->
        <g class="process">
          <ellipse cx="{proc_cx}" cy="{py}" rx="68" ry="38" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
          <text x="{proc_cx}" y="{py - 4 if len(lines) > 1 else py + 4}" font-size="13" font-weight="700" fill="#0f172a" text-anchor="middle">{lines[0]}</text>
          {f'<text x="{proc_cx}" y="{py + 15}" font-size="13" font-weight="700" fill="#0f172a" text-anchor="middle">{lines[1]}</text>' if len(lines) > 1 else ''}
        </g>

        <!-- Arrow from Login to Process ('valid user') -->
        <path d="M {lx + lr_x} 350 C {lx + lr_x + 60} 350, {proc_cx - 90} {py}, {proc_cx - 68} {py}" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
        """

        mid_x = (lx + lr_x + proc_cx - 68) / 2 - 10
        mid_y = (350 + py) / 2
        content += f"""
        <g transform="translate({mid_x}, {mid_y})">
          <rect x="-30" y="-8" width="60" height="15" fill="#ffffff" opacity="0.9"/>
          <text x="0" y="3" font-size="10" font-weight="600" fill="#2d6a4f" text-anchor="middle">valid user</text>
        </g>
        """

        store_y = py - 18
        content += draw_data_store(store_x, store_y, store_w, store_h, p["store"])

        p_right = proc_cx + 68
        content += f"""
        <!-- Process -> Store ({p['add']}) -->
        <path d="M {p_right + 4} {py - 10} L {store_x - 2} {py - 10}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        <text x="{(p_right + store_x)/2}" y="{py - 14}" font-size="10" font-weight="600" fill="#0f172a" text-anchor="middle">{p['add']}</text>

        <!-- Store -> Process ({p['get']}) -->
        <path d="M {store_x} {py + 10} L {p_right + 8} {py + 10}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        <text x="{(p_right + store_x)/2}" y="{py + 23}" font-size="10" font-weight="600" fill="#0f172a" text-anchor="middle">{p['get']}</text>
        """

    content += "</svg>"
    with open(os.path.join(OUTPUT_DIR, "wearlytics_dfd_level_1_user.svg"), "w") as f:
        f.write(content)


# -------------------------------------------------------------
# 3. WEARLYTICS LEVEL 1 ADMIN DFD
# -------------------------------------------------------------
def generate_wearlytics_level_1_admin():
    w, h = 1000, 720
    title = "LEVEL 1 ADMIN DFD"
    subtitle = "Decomposition of Administrator Functional Flows in Wearlytics"

    content = SVG_HEADER_TEMPLATE.format(width=w, height=h, title=title, subtitle=subtitle)

    # 1. External Entity: Admin
    ax, ay, aw, ah = 50, 310, 110, 60
    content += f"""
    <!-- External Entity: Admin -->
    <g class="entity">
      <rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="#ffffff" stroke="#1e293b" stroke-width="2" rx="4" filter="url(#shadow)"/>
      <text x="{ax + aw/2}" y="{ay + 36}" font-size="15" font-weight="700" fill="#0f172a" text-anchor="middle">Admin</text>
    </g>
    """

    # 2. Process: Login
    lx, ly, lr_x, lr_y = 270, 340, 58, 42
    content += f"""
    <!-- Process: Login -->
    <g class="process">
      <ellipse cx="{lx}" cy="{ly}" rx="{lr_x}" ry="{lr_y}" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
      <text x="{lx}" y="{ly + 5}" font-size="14" font-weight="700" fill="#0f172a" text-anchor="middle">Login</text>
    </g>

    <!-- Arrow Admin -> Login -->
    <path d="M {ax + aw} 340 L {lx - lr_x - 4} 340" fill="none" stroke="#1e293b" stroke-width="1.6" marker-end="url(#arrow)"/>
    <text x="195" y="332" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">credentials</text>
    """

    # 3. Data Store: login / users
    ds_login_x, ds_login_y, ds_login_w, ds_login_h = 200, 480, 140, 36
    content += draw_data_store(ds_login_x, ds_login_y, ds_login_w, ds_login_h, "login")

    # Arrows between Login and login Data Store
    content += f"""
    <!-- Login -> login -->
    <path d="M 245 380 L 245 476" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="185" y="425" width="58" height="15" fill="#ffffff"/>
    <text x="214" y="436" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">username</text>

    <!-- login -> Login -->
    <path d="M 295 476 L 295 382" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    <rect x="300" y="425" width="58" height="15" fill="#ffffff"/>
    <text x="329" y="436" font-size="11" font-weight="600" fill="#475569" text-anchor="middle">password</text>
    """

    # 4. Admin Sub-Processes
    admin_processes = [
        {"name": "Manage\nUsers", "store": "users", "add": "add / update user", "get": "get user details", "y": 160},
        {"name": "Manage Clothes\n& Presets", "store": "clothing_items", "add": "add preset items", "get": "get clothing data", "y": 290},
        {"name": "Manage AI Models\n& Rules", "store": "outfits", "add": "configure rules", "get": "get outfit metrics", "y": 420},
        {"name": "Feedback &\nAnalytics Log", "store": "outfit_feedback", "add": "log audit action", "get": "get feedback stats", "y": 550},
    ]

    proc_cx = 530
    store_x = 760
    store_w = 175
    store_h = 36

    for p in admin_processes:
        py = p["y"]
        lines = p["name"].split("\n")

        content += f"""
        <!-- Process: {p['name'].replace(chr(10), ' ')} -->
        <g class="process">
          <ellipse cx="{proc_cx}" cy="{py}" rx="68" ry="38" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
          <text x="{proc_cx}" y="{py - 4 if len(lines) > 1 else py + 4}" font-size="13" font-weight="700" fill="#0f172a" text-anchor="middle">{lines[0]}</text>
          {f'<text x="{proc_cx}" y="{py + 15}" font-size="13" font-weight="700" fill="#0f172a" text-anchor="middle">{lines[1]}</text>' if len(lines) > 1 else ''}
        </g>

        <!-- Arrow from Login to Process ('valid user') -->
        <path d="M {lx + lr_x} 340 C {lx + lr_x + 60} 340, {proc_cx - 90} {py}, {proc_cx - 68} {py}" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
        """

        mid_x = (lx + lr_x + proc_cx - 68) / 2 - 10
        mid_y = (340 + py) / 2
        content += f"""
        <g transform="translate({mid_x}, {mid_y})">
          <rect x="-30" y="-8" width="60" height="15" fill="#ffffff" opacity="0.9"/>
          <text x="0" y="3" font-size="10" font-weight="600" fill="#2d6a4f" text-anchor="middle">valid user</text>
        </g>
        """

        store_y = py - 18
        content += draw_data_store(store_x, store_y, store_w, store_h, p["store"])

        p_right = proc_cx + 68
        content += f"""
        <!-- Process -> Store ({p['add']}) -->
        <path d="M {p_right + 4} {py - 10} L {store_x - 2} {py - 10}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        <text x="{(p_right + store_x)/2}" y="{py - 14}" font-size="10" font-weight="600" fill="#0f172a" text-anchor="middle">{p['add']}</text>

        <!-- Store -> Process ({p['get']}) -->
        <path d="M {store_x} {py + 10} L {p_right + 8} {py + 10}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        <text x="{(p_right + store_x)/2}" y="{py + 23}" font-size="10" font-weight="600" fill="#0f172a" text-anchor="middle">{p['get']}</text>
        """

    content += "</svg>"
    with open(os.path.join(OUTPUT_DIR, "wearlytics_dfd_level_1_admin.svg"), "w") as f:
        f.write(content)


# -------------------------------------------------------------
# 4. LAW FIRM LEVEL 0 CONTEXT DIAGRAM (High fidelity reproduction of screenshot)
# -------------------------------------------------------------
def generate_lawfirm_level_0():
    w, h = 900, 480
    title = "LEVEL 0 CONTEXT DIAGRAM"
    subtitle = "Law Firm Management System — Context Flow"

    content = SVG_HEADER_TEMPLATE.format(width=w, height=h, title=title, subtitle=subtitle)

    # Left Entity
    lx, ly, lw, lh = 60, 180, 200, 100
    content += f"""
    <!-- Left Entity: Admin/Advocate/Petitioner/Court officer/Assistant -->
    <g class="entity">
      <rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
      <text x="{lx + lw/2}" y="{ly + 38}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">Admin/Advocate/Pe</text>
      <text x="{lx + lw/2}" y="{ly + 56}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">titioner/Court</text>
      <text x="{lx + lw/2}" y="{ly + 74}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">officer/Assistant</text>
    </g>
    """

    # Center Oval: Law Firm System
    cx, cy, rx, ry = 450, 230, 85, 80
    content += f"""
    <!-- Process: Law Firm System -->
    <g class="process">
      <ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
      <text x="{cx}" y="{cy - 8}" font-size="15" font-weight="600" fill="#0f172a" text-anchor="middle">Law Firm</text>
      <text x="{cx}" y="{cy + 14}" font-size="15" font-weight="600" fill="#0f172a" text-anchor="middle">System</text>
    </g>
    """

    # Right Entity
    rx_e, ry_e, rw_e, rh_e = 640, 180, 200, 100
    content += f"""
    <!-- Right Entity: Admin/Advocate/Petitioner/Court officer/Assistant -->
    <g class="entity">
      <rect x="{rx_e}" y="{ry_e}" width="{rw_e}" height="{rh_e}" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 38}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">Admin/Advocate/P</text>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 56}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">etitioner/Court</text>
      <text x="{rx_e + rw_e/2}" y="{ry_e + 74}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">officer/Assistant</text>
    </g>
    """

    # Arrows
    content += f"""
    <!-- Arrow Left -> Center ('request') -->
    <path d="M {lx + lw} 230 L {cx - rx - 4} 230" fill="none" stroke="#1e293b" stroke-width="1.6" marker-end="url(#arrow)"/>
    <text x="312" y="246" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">request</text>

    <!-- Arrow Center -> Right ('response') -->
    <path d="M {cx + rx + 4} 230 L {rx_e - 2} 230" fill="none" stroke="#1e293b" stroke-width="1.6" marker-end="url(#arrow)"/>
    <text x="588" y="246" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">response</text>
    """

    content += "</svg>"
    with open(os.path.join(OUTPUT_DIR, "lawfirm_dfd_level_0.svg"), "w") as f:
        f.write(content)


# -------------------------------------------------------------
# 5. LAW FIRM LEVEL 1 ADMIN DFD (Exact replica of screenshot)
# -------------------------------------------------------------
def generate_lawfirm_level_1_admin():
    w, h = 950, 680
    title = "LEVEL 1 ADMIN"
    subtitle = "Law Firm Management System — Admin Data Flow Diagram"

    content = SVG_HEADER_TEMPLATE.format(width=w, height=h, title=title, subtitle=subtitle)

    # 1. Admin Entity
    ax, ay, aw, ah = 50, 310, 100, 50
    content += f"""
    <!-- External Entity: Admin -->
    <g class="entity">
      <rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="#ffffff" stroke="#1e293b" stroke-width="1.6" filter="url(#shadow)"/>
      <text x="{ax + aw/2}" y="{ay + 30}" font-size="14" font-weight="600" fill="#0f172a" text-anchor="middle">Admin</text>
    </g>
    """

    # 2. Login Process
    lx, ly, lr_x, lr_y = 260, 335, 55, 40
    content += f"""
    <!-- Process: Login -->
    <g class="process">
      <ellipse cx="{lx}" cy="{ly}" rx="{lr_x}" ry="{lr_y}" fill="#ffffff" stroke="#1e293b" stroke-width="1.6" filter="url(#shadow)"/>
      <text x="{lx}" y="{ly + 5}" font-size="14" font-weight="600" fill="#0f172a" text-anchor="middle">Login</text>
    </g>

    <!-- Admin -> Login -->
    <path d="M {ax + aw} 335 L {lx - lr_x - 3} 335" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    """

    # 3. login Data Store
    ds_x, ds_y, ds_w, ds_h = 190, 470, 140, 34
    content += draw_data_store(ds_x, ds_y, ds_w, ds_h, "login")

    # Arrows Login <-> login
    content += f"""
    <!-- Down arrow: username -->
    <path d="M 235 375 L 235 466" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
    <g transform="translate(225, 425) rotate(-90)">
      <text x="0" y="0" font-size="11" font-weight="500" fill="#334155" text-anchor="middle">username</text>
    </g>

    <!-- Up arrow: password -->
    <path d="M 285 466 L 285 377" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
    <g transform="translate(295, 425) rotate(90)">
      <text x="0" y="0" font-size="11" font-weight="500" fill="#334155" text-anchor="middle">password</text>
    </g>
    """

    # 4. Processes
    law_processes = [
        {"name": "Manage\nPetitioner", "store": "Petitioner", "y": 150},
        {"name": "Manage\nAdvocate", "store": "Advocate", "y": 275},
        {"name": "Manage\nCourtOfficer", "store": "judge", "y": 400},
        {"name": "Complaint\nHandling", "store": "maildetails", "y": 525},
    ]

    proc_cx = 500
    store_x = 720
    store_w = 170
    store_h = 34

    for p in law_processes:
        py = p["y"]
        lines = p["name"].split("\n")

        content += f"""
        <!-- Process: {p['name'].replace(chr(10), ' ')} -->
        <g class="process">
          <ellipse cx="{proc_cx}" cy="{py}" rx="65" ry="36" fill="#ffffff" stroke="#1e293b" stroke-width="1.6" filter="url(#shadow)"/>
          <text x="{proc_cx}" y="{py - 4}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">{lines[0]}</text>
          <text x="{proc_cx}" y="{py + 14}" font-size="13" font-weight="600" fill="#0f172a" text-anchor="middle">{lines[1]}</text>
        </g>

        <!-- Arrow from Login to Process ('valid user') -->
        <path d="M {lx + lr_x} 335 L {proc_cx - 65} {py}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        """

        mid_x = (lx + lr_x + proc_cx - 65) / 2
        mid_y = (335 + py) / 2
        angle = 0
        if py < 300:
            angle = -25
        elif py > 450:
            angle = 25
        elif py > 350:
            angle = 12
        else:
            angle = -10

        content += f"""
        <g transform="translate({mid_x - 10}, {mid_y - 6}) rotate({angle})">
          <rect x="-25" y="-7" width="50" height="14" fill="#ffffff" opacity="0.9"/>
          <text x="0" y="4" font-size="10" font-weight="500" fill="#334155" text-anchor="middle">valid user</text>
        </g>
        """

        store_y = py - 17
        content += draw_data_store(store_x, store_y, store_w, store_h, p["store"])

        p_right = proc_cx + 65
        content += f"""
        <!-- add details -->
        <path d="M {p_right + 2} {py - 9} L {store_x - 2} {py - 9}" fill="none" stroke="#1e293b" stroke-width="1.3" marker-end="url(#arrow)"/>
        <text x="{(p_right + store_x)/2}" y="{py - 13}" font-size="10" font-weight="500" fill="#1e293b" text-anchor="middle">add details</text>

        <!-- get details -->
        <path d="M {store_x} {py + 9} L {p_right + 6} {py + 9}" fill="none" stroke="#1e293b" stroke-width="1.3" marker-end="url(#arrow)"/>
        <text x="{(p_right + store_x)/2}" y="{py + 21}" font-size="10" font-weight="500" fill="#1e293b" text-anchor="middle">get details</text>
        """

    content += "</svg>"
    with open(os.path.join(OUTPUT_DIR, "lawfirm_dfd_level_1_admin.svg"), "w") as f:
        f.write(content)


# -------------------------------------------------------------
# 6. WEARLYTICS LEVEL 1 OVERALL COMBINED SYSTEM DFD
# -------------------------------------------------------------
def generate_wearlytics_level_1_overall():
    w, h = 1100, 850
    title = "LEVEL 1 OVERALL SYSTEM DFD"
    subtitle = "Integrated Data Flow Decomposition for Wearlytics (User + Admin)"

    content = SVG_HEADER_TEMPLATE.format(width=w, height=h, title=title, subtitle=subtitle)

    content += f"""
    <!-- External Entity: User -->
    <g class="entity">
      <rect x="50" y="180" width="110" height="60" fill="#ffffff" stroke="#1e293b" stroke-width="2" rx="4" filter="url(#shadow)"/>
      <text x="105" y="216" font-size="16" font-weight="700" fill="#0f172a" text-anchor="middle">User</text>
    </g>

    <!-- External Entity: Admin -->
    <g class="entity">
      <rect x="50" y="580" width="110" height="60" fill="#ffffff" stroke="#1e293b" stroke-width="2" rx="4" filter="url(#shadow)"/>
      <text x="105" y="616" font-size="16" font-weight="700" fill="#0f172a" text-anchor="middle">Admin</text>
    </g>

    <!-- Process 1.0: Authentication -->
    <ellipse cx="260" cy="380" rx="65" ry="45" fill="#ffffff" stroke="#1e293b" stroke-width="2" filter="url(#shadow)"/>
    <text x="260" y="373" font-size="14" font-weight="700" fill="#0f172a" text-anchor="middle">1.0 Login /</text>
    <text x="260" y="393" font-size="14" font-weight="700" fill="#0f172a" text-anchor="middle">Authentication</text>

    <!-- Flows User/Admin to Login -->
    <path d="M 160 210 L 220 345" fill="none" stroke="#1e293b" stroke-width="1.6" marker-end="url(#arrow)"/>
    <text x="170" y="270" font-size="11" font-weight="600" fill="#475569">user credentials</text>

    <path d="M 160 610 L 220 415" fill="none" stroke="#1e293b" stroke-width="1.6" marker-end="url(#arrow)"/>
    <text x="165" y="525" font-size="11" font-weight="600" fill="#475569">admin credentials</text>
    """

    content += draw_data_store(190, 500, 140, 36, "users")
    content += f"""
    <path d="M 240 425 L 240 496" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    <text x="220" y="465" font-size="10" font-weight="600" fill="#475569">username</text>

    <path d="M 280 496 L 280 427" fill="none" stroke="#1e293b" stroke-width="1.5" marker-end="url(#arrow)"/>
    <text x="305" y="465" font-size="10" font-weight="600" fill="#475569">password</text>
    """

    all_procs = [
        {"num": "2.0", "name": "Manage\nWardrobe", "store": "clothing_items", "cy": 160, "add": "add/update item", "get": "fetch catalog"},
        {"num": "3.0", "name": "AI Outfit\nStylist", "store": "outfits", "cy": 300, "add": "save generated", "get": "get outfits"},
        {"num": "4.0", "name": "Weekly\nPlanner", "store": "weekly_plans", "cy": 440, "add": "save daily plan", "get": "fetch schedule"},
        {"num": "5.0", "name": "Analytics &\nFeedback", "store": "outfit_feedback", "cy": 580, "add": "submit rating", "get": "view stats"},
        {"num": "6.0", "name": "Admin\nControl", "store": "clothing_items", "cy": 720, "add": "manage presets", "get": "system audit"},
    ]

    mid_cx = 570
    ds_x = 860
    ds_w = 180

    for p in all_procs:
        pcy = p["cy"]
        lines = p["name"].split("\n")

        content += f"""
        <!-- Process {p['num']} -->
        <ellipse cx="{mid_cx}" cy="{pcy}" rx="70" ry="40" fill="#ffffff" stroke="#1e293b" stroke-width="1.8" filter="url(#shadow)"/>
        <text x="{mid_cx}" y="{pcy - 12}" font-size="11" font-weight="700" fill="#2d6a4f" text-anchor="middle">{p['num']}</text>
        <text x="{mid_cx}" y="{pcy + 4}" font-size="13" font-weight="700" fill="#0f172a" text-anchor="middle">{lines[0]}</text>
        {f'<text x="{mid_cx}" y="{pcy + 20}" font-size="13" font-weight="700" fill="#0f172a" text-anchor="middle">{lines[1]}</text>' if len(lines) > 1 else ''}

        <!-- Flow from Login -->
        <path d="M 325 380 C 390 380, {mid_cx - 90} {pcy}, {mid_cx - 70} {pcy}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        """

        content += draw_data_store(ds_x, pcy - 18, ds_w, 36, p["store"])

        content += f"""
        <path d="M {mid_cx + 70} {pcy - 9} L {ds_x - 2} {pcy - 9}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        <text x="{(mid_cx + 70 + ds_x)/2}" y="{pcy - 13}" font-size="10" font-weight="600" fill="#0f172a" text-anchor="middle">{p['add']}</text>

        <path d="M {ds_x} {pcy + 9} L {mid_cx + 75} {pcy + 9}" fill="none" stroke="#1e293b" stroke-width="1.4" marker-end="url(#arrow)"/>
        <text x="{(mid_cx + 70 + ds_x)/2}" y="{pcy + 22}" font-size="10" font-weight="600" fill="#0f172a" text-anchor="middle">{p['get']}</text>
        """

    content += "</svg>"
    with open(os.path.join(OUTPUT_DIR, "wearlytics_dfd_level_1_overall.svg"), "w") as f:
        f.write(content)


if __name__ == "__main__":
    generate_wearlytics_level_0()
    generate_wearlytics_level_1_user()
    generate_wearlytics_level_1_admin()
    generate_lawfirm_level_0()
    generate_lawfirm_level_1_admin()
    generate_wearlytics_level_1_overall()
    print("All SVGs successfully created in", OUTPUT_DIR)
