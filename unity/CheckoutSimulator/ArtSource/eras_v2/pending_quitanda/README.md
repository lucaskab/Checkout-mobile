# Quitanda (Era5_Quitanda) navy, ON HOLD

Lucas (26/10 20:47) asked to keep this saved: he hasn't decided yet whether he
wants it and will confirm in a few days. NOT installed in the game.

29/10 (bigger shops, branch `bigger-shops`): rebuilt at the new Quitanda size of
`CheckoutStall.Plans["Era5_Quitanda"]`: 1.5 m deeper (inner floor x -4.1..4.1,
y -2.4..4.1 = 53.3 m2, was 41), same front, door, window and counter; the
counter has a short return on its east end so the line runs along the east wall
(lane x ~3.65) instead of across the open front. The game's old Quitanda model
was grown the same way (cut and slid, `eras_v2.stretch_old`), so this one can
replace it without any other change.

- Export: `Era5_Quitanda.fbx` + `Era5_Quitanda_BaseColor.png`. To install, copy
  them over `Assets/Resources/CheckoutEras/` (same names, keep the .meta), run
  `play eventsstalls-quitanda,eventscrowd-quitanda.150.16.keep`, and commit.
  When installed, its produce rack outside counts as an obstacle (Plans solids
  `ERA5_Produce`).
- Source: `../eras_v2.blend`, builder `scripts/blender/eras_v2.py` (`build_quitanda()`, `QUI_PLAN`).
- Pictures: `era5_quitanda_before.jpg` (old), `era5_quitanda_v1_*.jpg` (v1, old size) and
  `era5_quitanda_bigger_*.jpg` (this one).
- Navy palette, open front, counter with register, crates outside, no text. Above 1.28 m is
  hidden in the game (CUT_ parts).
