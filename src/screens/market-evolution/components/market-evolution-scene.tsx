import { type ReactNode, useEffect, useRef } from "react";
import * as THREE from "three";
import { useFrame, useThree } from "./three-runtime";

export type EvolutionAreaId =
	| "core"
	| "fresh-wing"
	| "service-wing"
	| "stock-annex"
	| "premium-hall";

type MarketEvolutionSceneProps = {
	activeArea: EvolutionAreaId;
	rotation: number;
	zoom: number;
	unlockedAreaIds: EvolutionAreaId[];
};

export function MarketEvolutionScene({
	activeArea,
	rotation,
	zoom,
	unlockedAreaIds,
}: MarketEvolutionSceneProps) {
	const cityRef = useRef<THREE.Group>(null);

	useFrame((_, delta) => {
		if (!cityRef.current) {
			return;
		}

		const targetRotation = rotation + (activeArea === "core" ? 0 : 0.08);
		cityRef.current.rotation.y = THREE.MathUtils.lerp(
			cityRef.current.rotation.y,
			targetRotation,
			Math.min(1, delta * 5),
		);
	});

	return (
		<>
			<SceneCamera zoom={zoom} />
			<color attach="background" args={["#DFF2EC"]} />
			<ambientLight intensity={1.7} />
			<directionalLight position={[6, 10, 7]} intensity={2.2} />
			<hemisphereLight args={["#FFF8E8", "#75A990", 0.7]} />

			<group ref={cityRef} rotation={[0, rotation, 0]}>
				<CityBase />
				<MainMarket active={activeArea === "core"} />
				<AreaModule
					active={activeArea === "fresh-wing"}
					position={[-4.4, 0, -1.9]}
					unlocked={unlockedAreaIds.includes("fresh-wing")}
				>
					<FreshWing />
				</AreaModule>
				<AreaModule
					active={activeArea === "service-wing"}
					position={[4.1, 0, -1.9]}
					unlocked={unlockedAreaIds.includes("service-wing")}
				>
					<ServiceWing />
				</AreaModule>
				<AreaModule
					active={activeArea === "stock-annex"}
					position={[-3.9, 0, 3.25]}
					unlocked={unlockedAreaIds.includes("stock-annex")}
				>
					<StockAnnex />
				</AreaModule>
				<AreaModule
					active={activeArea === "premium-hall"}
					position={[3.8, 0, 3.25]}
					unlocked={unlockedAreaIds.includes("premium-hall")}
				>
					<PremiumHall />
				</AreaModule>
			</group>
		</>
	);
}

function SceneCamera({ zoom }: { zoom: number }) {
	const { camera } = useThree();

	useEffect(() => {
		camera.position.set(8.5, 9.5, 10.5);
		camera.lookAt(0, 0.4, 0.4);
		camera.zoom = zoom;
		camera.updateProjectionMatrix();
	}, [camera, zoom]);

	return null;
}

function CityBase() {
	return (
		<group>
			<mesh position={[0, -0.35, 0]}>
				<boxGeometry args={[12.5, 0.7, 10.5]} />
				<meshStandardMaterial color="#83C878" roughness={0.95} />
			</mesh>
			<mesh position={[0, 0.04, 0]}>
				<boxGeometry args={[11.8, 0.12, 9.8]} />
				<meshStandardMaterial color="#A9D97E" roughness={1} />
			</mesh>
			<Road position={[0, 0.12, -4.25]} rotation={0} length={11.8} />
			<Road position={[-5.15, 0.12, 0.6]} rotation={Math.PI / 2} length={8.2} />
			<Road position={[5.15, 0.12, 0.6]} rotation={Math.PI / 2} length={8.2} />
			<Planter position={[-5.1, 0.18, -3.05]} />
			<Planter position={[5.1, 0.18, -3.05]} />
			<Tree position={[-5, 0.2, 3.7]} scale={0.9} />
			<Tree position={[5, 0.2, 3.7]} scale={0.82} />
		</group>
	);
}

function Road({
	length,
	position,
	rotation,
}: {
	length: number;
	position: [number, number, number];
	rotation: number;
}) {
	return (
		<group position={position} rotation={[0, rotation, 0]}>
			<mesh>
				<boxGeometry args={[length, 0.08, 1.18]} />
				<meshStandardMaterial color="#D8B98C" roughness={0.9} />
			</mesh>
			{[-1, 0, 1, 2, 3].map((mark) => (
				<mesh key={mark} position={[-length / 2 + 1.2 + mark * 2, 0.05, 0]}>
					<boxGeometry args={[0.8, 0.025, 0.07]} />
					<meshStandardMaterial color="#FFF1D0" />
				</mesh>
			))}
		</group>
	);
}

function MainMarket({ active }: { active: boolean }) {
	return (
		<group>
			<mesh position={[0, 0.65, 0.3]}>
				<boxGeometry args={[5.8, 1.35, 4.2]} />
				<meshStandardMaterial
					color={active ? "#249E98" : "#2C8D8B"}
					roughness={0.72}
				/>
			</mesh>
			<mesh position={[0, 1.39, 0.3]}>
				<boxGeometry args={[6.15, 0.16, 4.5]} />
				<meshStandardMaterial color="#FFF0C6" roughness={0.8} />
			</mesh>
			<mesh position={[0, 1.5, -0.05]}>
				<boxGeometry args={[5.95, 0.12, 4.35]} />
				<meshStandardMaterial color="#F16F4D" roughness={0.78} />
			</mesh>
			<mesh position={[0, 1.75, 0.3]}>
				<boxGeometry args={[4.6, 0.45, 3.1]} />
				<meshStandardMaterial color="#F8DFAE" roughness={0.82} />
			</mesh>
			<Window position={[-1.75, 0.8, -1.84]} scale={[1.35, 0.7, 0.08]} />
			<Window position={[1.75, 0.8, -1.84]} scale={[1.35, 0.7, 0.08]} />
			<Door position={[0, 0.75, -1.91]} />
			<Awning position={[0, 1.45, -2.02]} />
			<Sign position={[0, 2.02, -1.82]} />
			{active && <GlowRing position={[0, 0.12, -2.35]} scale={[1.8, 1, 0.6]} />}
		</group>
	);
}

function AreaModule({
	active,
	children,
	position,
	unlocked,
}: {
	active: boolean;
	children: ReactNode;
	position: [number, number, number];
	unlocked: boolean;
}) {
	return (
		<group position={position}>
			{unlocked ? children : <LockedPlot active={active} />}
			{active && unlocked && (
				<GlowRing position={[0, 0.12, 0]} scale={[1.25, 1, 0.75]} />
			)}
		</group>
	);
}

function LockedPlot({ active }: { active: boolean }) {
	return (
		<group>
			<mesh position={[0, 0.2, 0]}>
				<boxGeometry args={[2.75, 0.28, 2.1]} />
				<meshStandardMaterial
					color={active ? "#B98E73" : "#A9A89A"}
					roughness={1}
				/>
			</mesh>
			<mesh position={[0, 0.5, 0]}>
				<boxGeometry args={[1.1, 0.5, 0.7]} />
				<meshStandardMaterial color="#C8C5B6" roughness={1} />
			</mesh>
			<mesh position={[0, 0.84, 0]} rotation={[0, Math.PI / 4, 0]}>
				<boxGeometry args={[0.5, 0.5, 0.08]} />
				<meshStandardMaterial color="#F5E9CE" roughness={0.9} />
			</mesh>
		</group>
	);
}

function FreshWing() {
	return (
		<group>
			<Plot position={[0, 0.14, 0]} color="#8B5D3A" />
			<Vegetable position={[-0.75, 0.35, -0.35]} color="#65B84B" />
			<Vegetable position={[0, 0.35, -0.35]} color="#E66A3A" />
			<Vegetable position={[0.75, 0.35, -0.35]} color="#F2A52F" />
			<Vegetable position={[-0.45, 0.35, 0.4]} color="#68B84E" />
			<Vegetable position={[0.45, 0.35, 0.4]} color="#E66A3A" />
			<ShortFence />
			<Sign position={[0, 1.42, -0.5]} color="#F16F4D" label="FRESCOS" />
		</group>
	);
}

function ServiceWing() {
	return (
		<group>
			<Plot position={[0, 0.14, 0]} color="#D9B36D" />
			<Checkout position={[-0.68, 0.45, 0]} />
			<Checkout position={[0.68, 0.45, 0]} />
			<QueuePost position={[-1.02, 0.3, -0.65]} />
			<QueuePost position={[1.02, 0.3, -0.65]} />
			<Sign position={[0, 1.42, -0.5]} color="#2C8D8B" label="ATENDIMENTO" />
		</group>
	);
}

function StockAnnex() {
	return (
		<group>
			<Plot position={[0, 0.14, 0]} color="#C99855" />
			<mesh position={[0, 0.95, 0]}>
				<boxGeometry args={[2.45, 1.65, 1.65]} />
				<meshStandardMaterial color="#D57C4F" roughness={0.82} />
			</mesh>
			<mesh position={[0, 1.85, 0]} rotation={[0, Math.PI / 4, 0]}>
				<coneGeometry args={[1.45, 0.72, 4]} />
				<meshStandardMaterial color="#8E4F41" roughness={0.9} />
			</mesh>
			<Door position={[0, 0.85, -0.84]} scale={[0.8, 1, 0.8]} />
			<Sign position={[0, 2.05, -0.86]} color="#F6B33D" label="ESTOQUE" />
		</group>
	);
}

function PremiumHall() {
	return (
		<group>
			<Plot position={[0, 0.14, 0]} color="#E9C879" />
			<mesh position={[0, 0.55, 0]}>
				<boxGeometry args={[2.35, 0.85, 1.75]} />
				<meshStandardMaterial color="#B783C4" roughness={0.72} />
			</mesh>
			<mesh position={[0, 1.18, 0]}>
				<cylinderGeometry args={[0.7, 0.85, 0.22, 12]} />
				<meshStandardMaterial
					color="#F2B03D"
					metalness={0.25}
					roughness={0.45}
				/>
			</mesh>
			<mesh position={[0, 1.55, 0]}>
				<cylinderGeometry args={[0.12, 0.12, 0.65, 8]} />
				<meshStandardMaterial
					color="#F2B03D"
					metalness={0.25}
					roughness={0.45}
				/>
			</mesh>
			<Sign position={[0, 1.72, -0.9]} color="#8B5C9E" label="PREMIUM" />
		</group>
	);
}

function Plot({
	color,
	position,
}: {
	color: string;
	position: [number, number, number];
}) {
	return (
		<mesh position={position}>
			<boxGeometry args={[2.75, 0.28, 2.1]} />
			<meshStandardMaterial color={color} roughness={0.92} />
		</mesh>
	);
}

function Vegetable({
	color,
	position,
}: {
	color: string;
	position: [number, number, number];
}) {
	return (
		<group position={position}>
			<mesh position={[0, 0.2, 0]}>
				<sphereGeometry args={[0.28, 8, 6]} />
				<meshStandardMaterial color={color} roughness={0.78} />
			</mesh>
			<mesh position={[0, 0.52, 0]}>
				<coneGeometry args={[0.16, 0.38, 6]} />
				<meshStandardMaterial color="#4A9D48" roughness={0.9} />
			</mesh>
		</group>
	);
}

function Checkout({ position }: { position: [number, number, number] }) {
	return (
		<group position={position}>
			<mesh>
				<boxGeometry args={[0.9, 0.6, 0.65]} />
				<meshStandardMaterial color="#249E98" roughness={0.75} />
			</mesh>
			<mesh position={[0, 0.42, 0]}>
				<boxGeometry args={[0.75, 0.08, 0.52]} />
				<meshStandardMaterial color="#FFF0C6" roughness={0.75} />
			</mesh>
		</group>
	);
}

function QueuePost({ position }: { position: [number, number, number] }) {
	return (
		<group position={position}>
			<mesh position={[0, 0.35, 0]}>
				<cylinderGeometry args={[0.08, 0.08, 0.7, 8]} />
				<meshStandardMaterial color="#F16F4D" roughness={0.75} />
			</mesh>
			<mesh position={[0, 0.7, 0]}>
				<sphereGeometry args={[0.13, 8, 6]} />
				<meshStandardMaterial color="#F2B03D" roughness={0.75} />
			</mesh>
		</group>
	);
}

function ShortFence() {
	return (
		<group position={[0, 0.4, 0.85]}>
			{[-0.95, 0, 0.95].map((x) => (
				<mesh key={x} position={[x, 0, 0]}>
					<boxGeometry args={[0.12, 0.7, 0.12]} />
					<meshStandardMaterial color="#9D6336" roughness={0.9} />
				</mesh>
			))}
			<mesh position={[0, 0.15, 0]}>
				<boxGeometry args={[2.05, 0.1, 0.1]} />
				<meshStandardMaterial color="#C68442" roughness={0.9} />
			</mesh>
		</group>
	);
}

function Window({
	position,
	scale = [1, 1, 1],
}: {
	position: [number, number, number];
	scale?: [number, number, number];
}) {
	return (
		<mesh position={position} scale={scale}>
			<boxGeometry args={[1, 1, 1]} />
			<meshStandardMaterial color="#9FE0DF" roughness={0.28} metalness={0.12} />
		</mesh>
	);
}

function Door({
	position,
	scale = [1, 1, 1],
}: {
	position: [number, number, number];
	scale?: [number, number, number];
}) {
	return (
		<mesh position={position} scale={scale}>
			<boxGeometry args={[1.1, 1.5, 0.11]} />
			<meshStandardMaterial color="#4CBBB7" roughness={0.3} metalness={0.12} />
		</mesh>
	);
}

function Awning({ position }: { position: [number, number, number] }) {
	return (
		<group position={position}>
			{[-1.6, -0.8, 0, 0.8, 1.6].map((x, index) => (
				<mesh key={x} position={[x, 0, 0]} rotation={[0.15, 0, 0]}>
					<boxGeometry args={[0.78, 0.2, 0.48]} />
					<meshStandardMaterial
						color={index % 2 === 0 ? "#F16F4D" : "#FFF0C6"}
						roughness={0.8}
					/>
				</mesh>
			))}
		</group>
	);
}

function Sign({
	color = "#F16F4D",
	label: _label,
	position,
}: {
	color?: string;
	label?: string;
	position: [number, number, number];
}) {
	return (
		<mesh position={position}>
			<boxGeometry args={[1.65, 0.33, 0.12]} />
			<meshStandardMaterial color={color} roughness={0.7} />
		</mesh>
	);
}

function Planter({ position }: { position: [number, number, number] }) {
	return (
		<group position={position}>
			<mesh position={[0, 0.2, 0]}>
				<cylinderGeometry args={[0.48, 0.56, 0.35, 10]} />
				<meshStandardMaterial color="#C9915B" roughness={0.85} />
			</mesh>
			<mesh position={[0, 0.48, 0]}>
				<dodecahedronGeometry args={[0.55, 0]} />
				<meshStandardMaterial color="#65B84B" roughness={0.95} />
			</mesh>
		</group>
	);
}

function Tree({
	position,
	scale,
}: {
	position: [number, number, number];
	scale: number;
}) {
	return (
		<group position={position} scale={scale}>
			<mesh position={[0, 0.75, 0]}>
				<cylinderGeometry args={[0.12, 0.16, 1.3, 7]} />
				<meshStandardMaterial color="#8D5A37" roughness={1} />
			</mesh>
			<mesh position={[0, 1.45, 0]}>
				<icosahedronGeometry args={[0.7, 1]} />
				<meshStandardMaterial color="#4C9E4D" roughness={0.95} />
			</mesh>
		</group>
	);
}

function GlowRing({
	position,
	scale,
}: {
	position: [number, number, number];
	scale: [number, number, number];
}) {
	return (
		<mesh position={position} rotation={[-Math.PI / 2, 0, 0]} scale={scale}>
			<ringGeometry args={[1.1, 1.32, 32]} />
			<meshBasicMaterial color="#F5B83B" transparent opacity={0.6} />
		</mesh>
	);
}
