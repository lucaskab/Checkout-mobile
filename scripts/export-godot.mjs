import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, "..");
const godotProject = path.join(projectRoot, "godot");
const exportRoot = path.join(projectRoot, "godot-exports");
const androidExport = path.join(exportRoot, "android", "CheckoutMarket");
const iosExport = path.join(exportRoot, "ios", "CheckoutMarket.pck");
const temporaryZip = path.join(os.tmpdir(), "CheckoutMarket-android.zip");

function findGodot() {
  const candidates = [
    process.env.GODOT_EDITOR,
    process.platform === "darwin"
      ? "/Applications/Godot.app/Contents/MacOS/Godot"
      : undefined,
    process.platform === "win32" ? "godot.exe" : "godot",
  ].filter(Boolean);

  for (const candidate of candidates) {
    if (path.isAbsolute(candidate) && fs.existsSync(candidate)) return candidate;
    const probe = spawnSync(candidate, ["--version"], { stdio: "ignore" });
    if (probe.status === 0) return candidate;
  }
  throw new Error(
    "Godot 4.5.1 was not found. Install it or set GODOT_EDITOR to its executable.",
  );
}

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function syncGeneratedNativeProjects() {
  const androidDestination = path.join(
    projectRoot,
    "android",
    "app",
    "src",
    "main",
    "assets",
    "CheckoutMarket",
  );
  if (fs.existsSync(path.join(projectRoot, "android"))) {
    fs.rmSync(androidDestination, { recursive: true, force: true });
    fs.mkdirSync(path.dirname(androidDestination), { recursive: true });
    fs.cpSync(androidExport, androidDestination, { recursive: true });
  }
}

const godot = findGodot();
run(godot, ["--headless", "--editor", "--path", godotProject, "--import", "--quit"]);

fs.rmSync(androidExport, { recursive: true, force: true });
fs.mkdirSync(androidExport, { recursive: true });
fs.mkdirSync(path.dirname(iosExport), { recursive: true });

run(godot, ["--headless", "--path", godotProject, "--export-pack", "Android", temporaryZip]);
run("tar", ["-xf", temporaryZip, "-C", androidExport]);
run(godot, ["--headless", "--path", godotProject, "--export-pack", "iOS", iosExport]);

fs.rmSync(temporaryZip, { force: true });
syncGeneratedNativeProjects();
console.log("Godot exports updated for Android and iOS.");
