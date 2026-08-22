import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDirectory, "..");
const godotPackageRoot = path.join(
  projectRoot,
  "node_modules",
  "@borndotcom",
  "react-native-godot",
);

function run(command, args) {
  const result = spawnSync(command, args, {
    cwd: projectRoot,
    stdio: "inherit",
    shell: false,
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}

function replaceInFile(filePath, before, after) {
  if (!fs.existsSync(filePath)) return;
  const source = fs.readFileSync(filePath, "utf8");
  if (source.includes(before)) {
    fs.writeFileSync(filePath, source.replace(before, after));
  }
}

if (!fs.existsSync(godotPackageRoot)) {
  throw new Error("@borndotcom/react-native-godot was not installed.");
}

if (process.platform === "win32") {
  run("powershell", [
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    path.join(scriptDirectory, "setup-godot-android.ps1"),
  ]);
} else {
  run(process.execPath, [
    path.join(godotPackageRoot, "scripts", "download-prebuilt.js"),
  ]);
}

replaceInFile(
  path.join(
    projectRoot,
    "node_modules",
    "react-native-worklets-core",
    "android",
    "CMakeLists.txt",
  ),
  `  target_link_libraries(\n    \${PACKAGE_NAME}\n    hermes-engine::libhermes\n  )`,
  `  if(TARGET hermes-engine::libhermes)\n    target_link_libraries(\${PACKAGE_NAME} hermes-engine::libhermes)\n  else()\n    target_link_libraries(\${PACKAGE_NAME} hermes-engine::hermesvm)\n  endif()`,
);

replaceInFile(
  path.join(
    godotPackageRoot,
    "android",
    "src",
    "main",
    "cpp",
    "native_godot_module_jni.h",
  ),
  "#include <react/jni/CxxModuleWrapper.h>\n",
  "",
);

console.log("LibGodot and React Native compatibility are ready.");
