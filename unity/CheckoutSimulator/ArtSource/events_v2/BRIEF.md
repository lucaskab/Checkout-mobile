# Event props v2 — brief for the asset agents (Oct 2026)

Game: "Checkout – Supermercado Simulator" (Unity 6, isometric camera from the front-right, soft painted look with
warm ink outlines). Each market event shows props on the street in front of the market. The concepts were
approved by Lucas (renders in ../Review/events_v2/<Event>.png, builders in ../events_kit.py). Your job: make the
props of your events MUCH better, in the same family as the game's current assets, then export them.

## Quality bar (the owner's words: "same style as the game, with the game's characters, same quality of textures, vertices and triangles")
- Real-world shapes and proportions, chamfered/bevelled edges, panel lines, small believable details (handles,
  hinges, bolts, vents, lamps, plates, cables, labels). Never plain boxes/spheres.
- Vivid colours of the current market palette (events_kit.C) — not the old pastel props.
- Procedural materials with texture (k.mat noise/bump, k.wood, k.stripes, L.corrugated/L.rustmetal, W.hazard...), baked
  to ONE BaseColor atlas per prop by events_kit.export_prop().
- Budgets (after bevels): vehicles 4k–7k tris (the game's Works_Pickup is 4.2k, Works_CherryPicker 6k, atlas 2048);
  street furniture / small props 300–2.5k tris (atlas 1024 or 512). Characters are NOT exported — the game spawns its own.
- Text on signs: Portuguese (Brazil), short, readable from the iso camera. No real brands/logos.

## Files and tools
- Repo root on the Mac: /Users/lucas-furini/repos/checkout. ArtSource = unity/CheckoutSimulator/ArtSource.
- Libraries: events_kit.py (diorama, actor(), vehicle(), preview(), prop_collection(), export_prop()), era_kit.py (k),
  works_kit.py (W: hazard(), wheels, truck cabs, machines), lot_kit.py (L: corrugated, rustmetal).
- Write YOUR code in ArtSource/events_v2/<your_module>.py (import events_kit as E). Do not edit events_kit.py except to
  fix a real bug (say so in your report); other agents work in parallel.
- Blender 5.2.1 runs on the Mac and is reachable through the Blender MCP tools
  (mcp__remote-devices__blender__execute_blender_code etc.; load them with ToolSearch "+blender"). Files in the repo can be
  read/written with mcp__remote-devices__device_bash (paths under $HOME/mnt/checkout/...) — that shell is a Linux VM
  sharing the folder; it cannot run Blender.
- IMPORTANT, PARALLEL SAFETY: several agents share that one Blender. Do NOT build/render/export in the interactive
  session. Do all real work in your OWN headless Blender process launched from execute_blender_code, e.g.
      import subprocess, bpy; subprocess.Popen([bpy.app.binary_path, "-b", "--factory-startup", "--python", SCRIPT, "--", ARGS],
          stdout=open(LOG, "w"), stderr=subprocess.STDOUT)
  then poll LOG / output files (each MCP call times out at 60 s). Your script must sys.path.insert ArtSource and
  scripts/blender itself.
- Look at your renders: stage the PNG with mcp__remote-devices__device_stage_files and Read it from
  /mnt/user-data/uploads/... . Iterate until it really looks good — compare with ../Review/works_v1/contact.png and
  ../Review/works_v2/contact_big.png (the game's newest vehicles/props) and with the concept render.

## Conventions for export
- One collection per exportable prop: E.prop_collection("<PropName>") ; model at the origin, ground at z=0 (NOT the
  sidewalk height .13), the side the camera should read facing -Y. Vehicles drive along +X.
- E.export_prop("<PropName>", size=1024|2048) writes Assets/Resources/EventProps2/<PropName>.fbx + _BaseColor.png
  and returns tris/dims. Prop names: PascalCase, prefixed by the event, e.g. Rush_CityBus, Rush_BusShelter.
- Animated parts the game should move (rotating prize wheel, ring light, spark, bunting) -> export them as their own
  prop (e.g. Sorteio_WheelDisc) with the origin at the pivot, and say how they should move.

## Review render for Lucas
For each event render ArtSource/Review/events_v2/v2_<Event>.png with E.diorama + your props placed like the concept
+ the game's characters via E.actor() (Customer_06..09; CustomerChild texture exists for kids), E.preview(...) settings.

## Report back (final message)
Per event: props exported (name, tris, atlas size, dims), the review PNG path, where each prop stands relative to the
market door / curb / road, how animated parts move, anything you could not do.
