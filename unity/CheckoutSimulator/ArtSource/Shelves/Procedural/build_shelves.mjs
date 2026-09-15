import fs from "node:fs/promises";
import * as THREE from "three";
import { GLTFExporter } from "three/addons/exporters/GLTFExporter.js";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

class NodeFileReader {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then((result) => {
      this.result = result;
      this.onloadend?.();
    });
  }
}

globalThis.FileReader ??= NodeFileReader;

const outDir = new URL("./models/", import.meta.url);
const materials = {
  cream: new THREE.MeshStandardMaterial({ color: 0xf7dfbb, roughness: 0.46 }),
  teal: new THREE.MeshStandardMaterial({ color: 0x43aeb4, roughness: 0.34 }),
  wood: new THREE.MeshStandardMaterial({ color: 0xb87038, roughness: 0.56 }),
  crate: new THREE.MeshStandardMaterial({ color: 0xc8894d, roughness: 0.59 }),
  bread: new THREE.MeshStandardMaterial({ color: 0xe9a555, roughness: 0.73 }),
  red: new THREE.MeshStandardMaterial({ color: 0xe8443b, roughness: 0.4 }),
  green: new THREE.MeshStandardMaterial({ color: 0x83bc3c, roughness: 0.45 }),
  orange: new THREE.MeshStandardMaterial({ color: 0xf58d2d, roughness: 0.42 }),
  yellow: new THREE.MeshStandardMaterial({ color: 0xf3cf38, roughness: 0.43 }),
  purple: new THREE.MeshStandardMaterial({ color: 0x9e4b91, roughness: 0.42 }),
  glass: new THREE.MeshPhysicalMaterial({ color: 0xf7e7cf, roughness: 0.12, transmission: 0.1, clearcoat: 0.35 }),
  jam: new THREE.MeshStandardMaterial({ color: 0xc94238, roughness: 0.29 }),
  cartonBlue: new THREE.MeshStandardMaterial({ color: 0x3aa4db, roughness: 0.36 }),
};

function roundedBox(name, size, position, material, radius = 0.04) {
  const mesh = new THREE.Mesh(new RoundedBoxGeometry(size[0], size[1], size[2], 2, radius), material);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

function sphere(name, radius, position, material, scale = [1, 1, 1]) {
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius, 12, 8), material);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.scale.set(...scale);
  return mesh;
}

function cylinder(name, radius, height, position, material) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, 12), material);
  mesh.name = name;
  mesh.position.set(...position);
  mesh.castShadow = true;
  return mesh;
}

function addCrate(parent, name, position, produceMaterial, count) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(...position);
  group.add(roundedBox(`${name}_base`, [0.56, 0.12, 0.38], [0, 0.06, 0], materials.crate, 0.025));
  for (const [x, z] of [[-0.25, -0.16], [0.25, -0.16], [-0.25, 0.16], [0.25, 0.16]]) {
    group.add(roundedBox(`${name}_corner`, [0.05, 0.26, 0.05], [x, 0.18, z], materials.wood, 0.015));
  }
  group.add(roundedBox(`${name}_frontSlat`, [0.5, 0.07, 0.035], [0, 0.18, -0.175], materials.wood, 0.012));
  group.add(roundedBox(`${name}_backSlat`, [0.5, 0.07, 0.035], [0, 0.18, 0.175], materials.wood, 0.012));
  for (let index = 0; index < count; index += 1) {
    const x = -0.18 + (index % 3) * 0.18;
    const z = -0.09 + Math.floor(index / 3) * 0.13;
    group.add(sphere(`${name}_produce_${index + 1}`, 0.095, [x, 0.28 + (index % 2) * 0.025, z], produceMaterial, [1, 0.92, 1]));
  }
  parent.add(group);
}

function addJar(parent, name, position, fillMaterial) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(...position);
  group.add(cylinder(`${name}_glass`, 0.115, 0.25, [0, 0.125, 0], materials.glass));
  group.add(cylinder(`${name}_fill`, 0.098, 0.17, [0, 0.1, 0], fillMaterial));
  group.add(cylinder(`${name}_lid`, 0.12, 0.035, [0, 0.265, 0], materials.yellow));
  parent.add(group);
}

function addCarton(parent, name, position, material) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(...position);
  group.add(roundedBox(`${name}_body`, [0.2, 0.4, 0.16], [0, 0.2, 0], material, 0.018));
  group.add(roundedBox(`${name}_top`, [0.18, 0.09, 0.14], [0, 0.435, 0], materials.cream, 0.012));
  parent.add(group);
}

function addBread(parent, name, position) {
  const loaf = roundedBox(name, [0.38, 0.16, 0.2], position, materials.bread, 0.08);
  loaf.rotation.z = -0.08;
  parent.add(loaf);
}

function createShelfFrame() {
  const root = new THREE.Group();
  root.name = "SupermarketShelf";
  root.add(roundedBox("BackPanel", [2.36, 2.45, 0.10], [0, 1.28, 0.24], materials.cream, 0.08));
  root.add(roundedBox("LeftUpright", [0.19, 2.72, 0.52], [-1.18, 1.36, 0], materials.cream, 0.085));
  root.add(roundedBox("RightUpright", [0.19, 2.72, 0.52], [1.18, 1.36, 0], materials.cream, 0.085));
  root.add(roundedBox("TopCrossbar", [2.36, 0.18, 0.52], [0, 2.61, 0], materials.cream, 0.075));
  root.add(roundedBox("LeftFoot", [0.44, 0.16, 0.66], [-1.02, 0.08, 0.03], materials.teal, 0.05));
  root.add(roundedBox("RightFoot", [0.44, 0.16, 0.66], [1.02, 0.08, 0.03], materials.teal, 0.05));
  for (const [index, y] of [0.38, 1.17, 1.96].entries()) {
    root.add(roundedBox(`ShelfDeck_${index + 1}`, [2.17, 0.09, 0.52], [0, y, 0], materials.wood, 0.03));
    root.add(roundedBox(`TealFrontRail_${index + 1}`, [2.23, 0.16, 0.10], [0, y + 0.025, -0.25], materials.teal, 0.045));
  }
  return root;
}

function populateFull(root) {
  const stock = new THREE.Group();
  stock.name = "FullStock";
  addCrate(stock, "TopBananas", [-0.75, 2.03, -0.02], materials.yellow, 8);
  addCrate(stock, "TopApples", [-0.14, 2.03, -0.02], materials.red, 8);
  addCrate(stock, "TopOranges", [0.48, 2.03, -0.02], materials.orange, 8);
  addBread(stock, "TopBreadA", [0.93, 2.09, -0.04]);
  addBread(stock, "TopBreadB", [0.93, 2.24, -0.03]);
  for (let index = 0; index < 5; index += 1) addJar(stock, `MiddleJar_${index + 1}`, [-0.78 + index * 0.3, 1.22, -0.05], index % 2 ? materials.orange : materials.jam);
  addCarton(stock, "MiddleCartonA", [0.58, 1.22, -0.04], materials.cartonBlue);
  addCarton(stock, "MiddleCartonB", [0.83, 1.22, -0.04], materials.cream);
  addCrate(stock, "BottomCarrots", [-0.72, 0.45, -0.02], materials.orange, 7);
  addCrate(stock, "BottomLettuce", [-0.12, 0.45, -0.02], materials.green, 6);
  addCrate(stock, "BottomTomatoes", [0.48, 0.45, -0.02], materials.red, 7);
  addCrate(stock, "BottomOnions", [0.92, 0.45, -0.02], materials.purple, 5);
  root.add(stock);
}

function populatePartial(root) {
  const stock = new THREE.Group();
  stock.name = "PartialStock";
  addCrate(stock, "TopApples", [-0.7, 2.03, -0.02], materials.red, 5);
  addJar(stock, "TopJarA", [0.28, 2.04, -0.03], materials.jam);
  addCarton(stock, "TopCarton", [0.78, 2.03, -0.03], materials.cartonBlue);
  addCrate(stock, "MiddleBananas", [-0.67, 1.23, -0.02], materials.yellow, 4);
  addBread(stock, "MiddleBread", [0.72, 1.28, -0.05]);
  addJar(stock, "BottomJar", [-0.76, 0.45, -0.03], materials.orange);
  addCrate(stock, "BottomApples", [0.72, 0.45, -0.02], materials.green, 4);
  root.add(stock);
}

function createVariant(name) {
  const root = createShelfFrame();
  root.name = name;
  if (name === "ShelfFull") populateFull(root);
  if (name === "ShelfPartial") populatePartial(root);
  return root;
}

async function writeGlb(name) {
  const exporter = new GLTFExporter();
  const asset = createVariant(name);
  // The Groceries fixture in MarketWorld is 2.10 Unity units tall and 6.70 units wide.
  // These dimensions produce a 2.12 x 2.04 x 0.66 unit shelf, leaving room for aisles and NPC paths.
  asset.scale.set(0.9, 0.75, 1);
  const glb = await new Promise((resolve, reject) => {
    exporter.parse(asset, resolve, reject, { binary: true, onlyVisible: true, trs: false });
  });
  await fs.mkdir(outDir, { recursive: true });
  await fs.writeFile(new URL(`${name}.glb`, outDir), Buffer.from(glb));
}

await Promise.all([writeGlb("ShelfFull"), writeGlb("ShelfPartial"), writeGlb("ShelfEmpty")]);
