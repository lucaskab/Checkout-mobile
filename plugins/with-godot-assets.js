const fs = require("node:fs");
const path = require("node:path");
const {
  IOSConfig,
  withDangerousMod,
  withGradleProperties,
  withXcodeProject,
} = require("expo/config-plugins");

const PROJECT_NAME = "CheckoutMarket";

function replaceDirectory(source, destination) {
  if (!fs.existsSync(source)) {
    throw new Error(`Godot export not found: ${source}`);
  }

  fs.rmSync(destination, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.cpSync(source, destination, { recursive: true });
}

function setGradleProperty(properties, key, value) {
  const next = properties.filter((item) => item.key !== key);
  next.push({ type: "property", key, value });
  return next;
}

function withAndroidGodot(config) {
  config = withGradleProperties(config, (gradleConfig) => {
    gradleConfig.modResults = setGradleProperty(
      gradleConfig.modResults,
      "android.minSdkVersion",
      "29",
    );
    gradleConfig.modResults = setGradleProperty(
      gradleConfig.modResults,
      "reactNativeArchitectures",
      "armeabi-v7a,arm64-v8a",
    );
    return gradleConfig;
  });

  return withDangerousMod(config, ["android", (androidConfig) => {
    const projectRoot = androidConfig.modRequest.projectRoot;
    const source = path.join(
      projectRoot,
      "godot-exports",
      "android",
      PROJECT_NAME,
    );
    const destination = path.join(
      androidConfig.modRequest.platformProjectRoot,
      "app",
      "src",
      "main",
      "assets",
      PROJECT_NAME,
    );
    replaceDirectory(source, destination);
    return androidConfig;
  }]);
}

function withIosGodot(config) {
  return withXcodeProject(config, (iosConfig) => {
    const projectRoot = iosConfig.modRequest.projectRoot;
    const platformRoot = iosConfig.modRequest.platformProjectRoot;
    const xcodeProject = iosConfig.modResults;
    const iosProjectName = IOSConfig.XcodeUtils.getProjectName(projectRoot);
    const source = path.join(
      projectRoot,
      "godot-exports",
      "ios",
      `${PROJECT_NAME}.pck`,
    );
    const relativeDestination = path.join(
      iosProjectName,
      `${PROJECT_NAME}.pck`,
    );
    const destination = path.join(platformRoot, relativeDestination);

    if (!fs.existsSync(source)) {
      throw new Error(`Godot export not found: ${source}`);
    }

    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.copyFileSync(source, destination);
    IOSConfig.XcodeUtils.ensureGroupRecursively(xcodeProject, "Resources");
    IOSConfig.XcodeUtils.addResourceFileToGroup({
      filepath: relativeDestination,
      groupName: "Resources",
      project: xcodeProject,
      isBuildFile: true,
      verbose: true,
    });
    return iosConfig;
  });
}

module.exports = function withGodotAssets(config) {
  config = withAndroidGodot(config);
  config = withIosGodot(config);
  return config;
};
