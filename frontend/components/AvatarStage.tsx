"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";

import type { NonverbalCue, TurnResult } from "@/lib/types";

type AvatarStageProps = {
  emotion: TurnResult["emotion"];
  cues: NonverbalCue[];
  speaking?: boolean;
};

type BoneName =
  | "hips" | "spine" | "chest" | "upperChest" | "neck" | "head"
  | "leftShoulder" | "rightShoulder" | "leftUpperArm" | "rightUpperArm"
  | "leftLowerArm" | "rightLowerArm" | "leftHand" | "rightHand";

const BONE_ALIASES: Record<BoneName, string[]> = {
  hips: ["hips", "pelvis", "root", "mixamorighips", "bip01", "bip01pelvis"],
  spine: ["spine", "spine01", "mixamorigspine", "bip01spine"],
  chest: ["spine1", "spine02", "chest", "mixamorigspine1", "bip01spine1"],
  upperChest: ["spine2", "spine03", "upperchest", "mixamorigspine2", "bip01spine2"],
  neck: ["neck", "neck01", "mixamorigneck", "bip01neck"],
  head: ["head", "mixamorighead", "bip01head"],
  leftShoulder: ["leftshoulder", "claviclel", "mixamorigleftshoulder", "bip01lclavicle"],
  rightShoulder: ["rightshoulder", "clavicler", "mixamorigrightshoulder", "bip01rclavicle"],
  leftUpperArm: ["leftarm", "leftupperarm", "upperarml", "mixamorigleftarm", "bip01lupperarm"],
  rightUpperArm: ["rightarm", "rightupperarm", "upperarmr", "mixamorigrightarm", "bip01rupperarm"],
  leftLowerArm: ["leftforearm", "leftlowerarm", "lowerarml", "mixamorigleftforearm", "bip01lforearm"],
  rightLowerArm: ["rightforearm", "rightlowerarm", "lowerarmr", "mixamorigrightforearm", "bip01rforearm"],
  leftHand: ["lefthand", "handl", "mixamoringlefthand", "bip01lhand"],
  rightHand: ["righthand", "handr", "mixamorigrighthand", "bip01rhand"],
};

const FACE: Record<string, Record<string, number>> = {
  neutral: {},
  sad: { browInnerUp: .86, mouthFrownLeft: .72, mouthFrownRight: .72, eyeSquintLeft: .16, eyeSquintRight: .16 },
  angry: { browDownLeft: .92, browDownRight: .92, eyeSquintLeft: .4, eyeSquintRight: .4, mouthPressLeft: .62, mouthPressRight: .62 },
  anxious: { browInnerUp: .82, eyeWideLeft: .52, eyeWideRight: .52, mouthPressLeft: .48, mouthPressRight: .48 },
  hurt: { browInnerUp: .96, mouthFrownLeft: .84, mouthFrownRight: .84, cheekSquintLeft: .28, cheekSquintRight: .28 },
  withdrawn: { eyeLookDownLeft: .7, eyeLookDownRight: .7, eyeSquintLeft: .28, eyeSquintRight: .28, mouthFrownLeft: .46, mouthFrownRight: .46 },
};

const norm = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");
const clamp = (value: number) => Math.max(0, Math.min(1, value));

export default function AvatarStage({ emotion, cues, speaking = false }: AvatarStageProps) {
  const hostRef = useRef<HTMLDivElement>(null);
  const liveRef = useRef({ emotion, cues, speaking });
  const [status, setStatus] = useState("실사형 GLB 불러오는 중");

  useEffect(() => { liveRef.current = { emotion, cues, speaking }; }, [emotion, cues, speaking]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xe8e5e0);
    const camera = new THREE.PerspectiveCamera(32, 1, .01, 50);
    camera.position.set(0, 1.47, 1.52);
    camera.lookAt(0, 1.29, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.shadowMap.enabled = false;
    host.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x786f69, 2.2));
    const key = new THREE.DirectionalLight(0xfff4e8, 2.6);
    key.position.set(-2.2, 4, 3.1);
    scene.add(key);
    const fill = new THREE.DirectionalLight(0xcfe2ff, 1.15);
    fill.position.set(2.4, 2.2, 1.1);
    scene.add(fill);

    let root: THREE.Object3D | null = null;
    const bones = {} as Record<BoneName, THREE.Object3D | null>;
    const base = new Map<THREE.Object3D, THREE.Quaternion>();
    const morphs = new Map<string, Array<{ mesh: THREE.Mesh; index: number }>>();
    let isRocketbox = false;
    let animationFrame = 0;
    let nextBlink = 1.8;
    let blinkUntil = 0;

    function resize() {
      if (!host) return;
      const width = Math.max(1, host.clientWidth);
      const height = Math.max(1, host.clientHeight);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    }
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();

    function cue(id: string): number {
      const found = liveRef.current.cues.find(item => item.id === id);
      return found ? found.intensity : 0;
    }
    function rotate(name: BoneName, pitch = 0, yaw = 0, roll = 0) {
      const bone = bones[name];
      if (!bone) return;
      const euler = isRocketbox
        ? new THREE.Euler(THREE.MathUtils.degToRad(yaw), THREE.MathUtils.degToRad(roll), THREE.MathUtils.degToRad(pitch), "XYZ")
        : new THREE.Euler(THREE.MathUtils.degToRad(pitch), THREE.MathUtils.degToRad(yaw), THREE.MathUtils.degToRad(roll), "XYZ");
      bone.quaternion.multiply(new THREE.Quaternion().setFromEuler(euler));
    }
    function rotateToward(bone: THREE.Object3D | null, effector: THREE.Object3D | null, target: THREE.Vector3, weight: number) {
      if (!bone || !effector || !bone.parent) return;
      root?.updateMatrixWorld(true);
      const joint = bone.getWorldPosition(new THREE.Vector3());
      const current = effector.getWorldPosition(new THREE.Vector3()).sub(joint);
      const desired = target.clone().sub(joint);
      if (current.lengthSq() < 1e-8 || desired.lengthSq() < 1e-8) return;
      const deltaWorld = new THREE.Quaternion().setFromUnitVectors(current.normalize(), desired.normalize());
      const desiredWorld = deltaWorld.multiply(bone.getWorldQuaternion(new THREE.Quaternion()));
      const desiredLocal = bone.parent.getWorldQuaternion(new THREE.Quaternion()).invert().multiply(desiredWorld);
      bone.quaternion.slerp(desiredLocal, clamp(weight));
    }
    function solveArm(side: "left" | "right", localTarget: THREE.Vector3, strength = 1, localPole?: THREE.Vector3) {
      if (!root) return;
      const upper = bones[`${side}UpperArm` as BoneName];
      const lower = bones[`${side}LowerArm` as BoneName];
      const hand = bones[`${side}Hand` as BoneName];
      if (!upper || !lower || !hand) return;
      const rootPosition = root.getWorldPosition(new THREE.Vector3());
      const rootRotation = root.getWorldQuaternion(new THREE.Quaternion());
      const target = localTarget.clone().applyQuaternion(rootRotation).add(rootPosition);
      const sign = side === "left" ? 1 : -1;
      const pole = (localPole ?? new THREE.Vector3(sign * .58, 1.03, .18)).clone().applyQuaternion(rootRotation).add(rootPosition);
      const weight = .58 + clamp(strength) * .38;
      for (let i = 0; i < 4; i += 1) {
        root.updateMatrixWorld(true);
        const shoulder = upper.getWorldPosition(new THREE.Vector3());
        const elbow = lower.getWorldPosition(new THREE.Vector3());
        const wrist = hand.getWorldPosition(new THREE.Vector3());
        const upperLength = Math.max(.001, shoulder.distanceTo(elbow));
        const lowerLength = Math.max(.001, elbow.distanceTo(wrist));
        const toTarget = target.clone().sub(shoulder);
        const distance = Math.max(.001, Math.min(toTarget.length(), upperLength + lowerLength - .002));
        const direction = toTarget.normalize();
        const poleDirection = pole.clone().sub(shoulder).addScaledVector(direction, -pole.clone().sub(shoulder).dot(direction));
        if (poleDirection.lengthSq() < 1e-8) poleDirection.set(sign, 0, .15);
        poleDirection.normalize();
        const along = THREE.MathUtils.clamp((upperLength ** 2 - lowerLength ** 2 + distance ** 2) / (2 * distance), -upperLength, upperLength);
        const bend = Math.sqrt(Math.max(0, upperLength ** 2 - along ** 2));
        const desiredElbow = shoulder.clone().addScaledVector(direction, along).addScaledVector(poleDirection, bend);
        rotateToward(upper, lower, desiredElbow, weight);
        root.updateMatrixWorld(true);
        rotateToward(lower, hand, target, weight);
      }
    }
    function setMorph(name: string, value: number) {
      const wanted = norm(name);
      const entries = [...morphs.entries()].filter(([key]) => key === wanted || key.endsWith(wanted));
      for (const [, bindings] of entries) for (const binding of bindings) {
        const influences = (binding.mesh as THREE.Mesh & { morphTargetInfluences?: number[] }).morphTargetInfluences;
        if (influences) influences[binding.index] = clamp(value);
      }
    }
    function resetMorphs() {
      for (const bindings of morphs.values()) for (const binding of bindings) {
        const influences = (binding.mesh as THREE.Mesh & { morphTargetInfluences?: number[] }).morphTargetInfluences;
        if (influences) influences[binding.index] = 0;
      }
    }

    new GLTFLoader().load(
      process.env.NEXT_PUBLIC_AVATAR_MODEL_URL ?? "/models/Female_Adult_01_facial_1024.glb",
      gltf => {
        root = gltf.scene;
        const nodes: THREE.Object3D[] = [];
        root.traverse(node => {
          nodes.push(node);
          const mesh = node as THREE.Mesh & { morphTargetDictionary?: Record<string, number> };
          if (mesh.isMesh && mesh.morphTargetDictionary) {
            for (const [raw, index] of Object.entries(mesh.morphTargetDictionary)) {
              const key = norm(raw);
              if (!morphs.has(key)) morphs.set(key, []);
              morphs.get(key)!.push({ mesh, index });
            }
          }
        });
        isRocketbox = nodes.some(node => norm(node.name) === "bip01");
        for (const [semantic, aliases] of Object.entries(BONE_ALIASES) as Array<[BoneName, string[]]>) {
          bones[semantic] = nodes.find(node => aliases.includes(norm(node.name))) ?? null;
        }
        const box = new THREE.Box3().setFromObject(root);
        const size = box.getSize(new THREE.Vector3());
        const center = box.getCenter(new THREE.Vector3());
        root.position.set(-center.x, -box.min.y, -center.z);
        root.scale.setScalar(1.72 / (Math.max(size.x, size.y, size.z) || 1));
        scene.add(root);
        root.updateMatrixWorld(true);
        Object.values(bones).forEach(bone => { if (bone) base.set(bone, bone.quaternion.clone()); });
        const arkitNames = ["browinnerup", "browdownleft", "mouthsmileleft", "mouthfrownleft", "eyewideleft"];
        const arkitCount = arkitNames.filter(name => [...morphs.keys()].some(key => key.endsWith(name))).length;
        setStatus(arkitCount >= 4 ? "실사형 GLB · ARKit 표정 호환 · 절차적 포즈" : "실사형 GLB · 기본 표정 · 절차적 포즈");
      },
      progress => { if (progress.total) setStatus(`모델 로딩 ${Math.round(progress.loaded / progress.total * 100)}%`); },
      () => setStatus("모델 로드 실패 · public/models 파일을 확인하세요"),
    );

    const clock = new THREE.Clock();
    function animate() {
      animationFrame = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();
      if (root) {
        base.forEach((value, bone) => bone.quaternion.copy(value));
        root.rotation.y = 0;
        root.position.x = 0;
        const lean = Math.max(cue("posture.lean_forward"), cue("space.close_to_table"));
        const recline = Math.max(cue("posture.recline"), cue("space.increase_distance"));
        const hunch = cue("posture.hunch");
        rotate("spine", lean * 12 - recline * 14 + hunch * 8);
        rotate("chest", lean * 15 - recline * 15 + hunch * 13 + Math.sin(t * 1.5) * .5);
        rotate("neck", -lean * 6 + recline * 5 + hunch * 4);

        const crossed = Math.max(cue("posture.arms_crossed"), cue("space.shield_with_object"));
        const wring = Math.max(cue("hand.finger_wring"), cue("hand.pick_nails"), cue("hand.fidget_object"));
        if (crossed) {
          solveArm("left", new THREE.Vector3(-.055, 1.17, .18), crossed, new THREE.Vector3(.58, 1.08, .38));
          solveArm("right", new THREE.Vector3(.055, 1.11, .19), crossed, new THREE.Vector3(-.58, 1.02, .38));
        } else if (wring) {
          const shift = Math.sin(t * 6.5) * .018 * wring;
          solveArm("left", new THREE.Vector3(.035 + shift, 1.16, .24), wring);
          solveArm("right", new THREE.Vector3(-.035 - shift, 1.16, .26), wring);
        } else {
          solveArm("left", new THREE.Vector3(.14, .76, .1), .94);
          solveArm("right", new THREE.Vector3(-.14, .76, .11), .94);
        }
        const avoid = Math.max(cue("gaze.avoid_counselor"), cue("gaze.topic_avoid"));
        const floor = cue("gaze.floor_or_wall");
        rotate("head", floor * 17, -avoid * 18 + Math.sin(t * .5) * .35, 0);
        rotate("neck", floor * 9, -avoid * 8, 0);
        const turnAway = Math.max(cue("posture.turn_away"), cue("behavior.topic_turn_shift"));
        root.rotation.y += turnAway * .4;

        resetMorphs();
        const profile = FACE[liveRef.current.emotion] ?? FACE.neutral;
        for (const [name, value] of Object.entries(profile)) setMorph(name, value);
        if (cue("face.frown")) for (const name of ["browDownLeft", "browDownRight", "mouthPressLeft", "mouthPressRight"]) setMorph(name, .82);
        if (cue("face.lip_press_bite")) for (const name of ["mouthPressLeft", "mouthPressRight"]) setMorph(name, .92);
        if (t >= nextBlink) { blinkUntil = t + .12; nextBlink = t + 2.1 + Math.random() * 2.8; }
        const blink = t < blinkUntil ? 1 : 0;
        setMorph("eyeBlinkLeft", blink);
        setMorph("eyeBlinkRight", blink);
        setMorph("eyesClosed", blink);
        if (liveRef.current.speaking) {
          const mouth = .2 + Math.abs(Math.sin(t * 9.4)) * .54;
          setMorph("viseme_aa", mouth);
          setMorph("jawOpen", mouth * .66);
        }
      }
      renderer.render(scene, camera);
    }
    animate();
    return () => {
      cancelAnimationFrame(animationFrame);
      observer.disconnect();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return (
    <div className="avatar-stage">
      <div ref={hostRef} className="avatar-canvas" aria-label="가상 내담자 3D 아바타" />
      <div className="avatar-status">{status}</div>
      <div className="avatar-cues">
        {cues.length ? cues.map(item => <span key={item.id}>{item.label}</span>) : <span>차분한 기본 자세</span>}
      </div>
    </div>
  );
}
