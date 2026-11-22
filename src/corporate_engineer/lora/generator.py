"""
Synthetic dataset generator for Gemini LoRA DarkFactory training (ADR-020).
"""

import json
import random

from corporate_engineer.models import LoraDatasetConfig, LoraDomain, LoraTrainingSample

DARKFACTORY_SYSTEM_INSTRUCTION = (
    "You are a DarkFactory Visual Automation & Motion Graphics Architect specializing in "
    "cyber-industrial aesthetic, algorithmic choreography, and production-grade tool orchestration."
)

REMOTION_TEMPLATES = [
    (
        "Generate a DarkFactory cyber-industrial lower third with spring animation and telemetry stats.",
        """import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const DarkFactoryLowerThird: React.FC<{ title: string; subtitle: string }> = ({
    title = 'DARKFACTORY ARCHITECT',
    subtitle = 'AUTONOMOUS CORE ONLINE',
}) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const enterProgress = spring({
        frame,
        fps,
        config: { damping: 14, mass: 0.8 },
    });

    const glowOpacity = interpolate(frame, [0, 20, 40], [0, 1, 0.7], {
        extrapolateRight: 'clamp',
    });

    return (
        <div
            style={{
                position: 'absolute',
                bottom: 80,
                left: 100,
                backgroundColor: '#0a0a0c',
                borderLeft: '4px solid #00ffcc',
                padding: '18px 32px',
                transform: `translateX(${(1 - enterProgress) * -120}px)`,
                opacity: enterProgress,
                fontFamily: 'monospace',
            }}
        >
            <div style={{ color: '#00ffcc', fontSize: 24, fontWeight: 'bold' }}>
                {title}
            </div>
            <div style={{ color: '#888888', fontSize: 14, opacity: glowOpacity }}>
                {subtitle}
            </div>
        </div>
    );
};
""",
    ),
    (
        "Build a high-contrast dark telemetry HUD component in Remotion with reactive frame interpolation.",
        """import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';

export const TelemetryHUD: React.FC = () => {
    const frame = useCurrentFrame();
    const scanline = interpolate(frame % 60, [0, 60], [0, 100]);

    return (
        <div
            style={{
                width: 480,
                height: 280,
                backgroundColor: '#000',
                border: '1px solid #222',
                position: 'relative',
                overflow: 'hidden',
                fontFamily: 'Courier, monospace',
            }}
        >
            <div style={{ padding: 20, color: '#00e5ff' }}>
                <span>[NODE 0x1A] STATUS: OPERATIONAL</span>
            </div>
            <div
                style={{
                    position: 'absolute',
                    top: `${scanline}%`,
                    left: 0,
                    right: 0,
                    height: 2,
                    backgroundColor: '#00ff88',
                }}
            />
        </div>
    );
};
""",
    ),
    (
        "Create an industrial glitch transition in Remotion for brand reveals.",
        """import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const GlitchBrandReveal: React.FC<{ brandText: string }> = ({
    brandText = 'DARKFACTORY',
}) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();

    const scale = spring({ frame, fps, config: { damping: 12 } });
    const shift = interpolate(frame, [10, 12, 14, 16], [0, 8, -6, 0], {
        extrapolateRight: 'clamp',
    });

    return (
        <div
            style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                width: '100%',
                height: '100%',
                backgroundColor: '#111',
            }}
        >
            <h1
                style={{
                    fontSize: 72,
                    color: '#ffffff',
                    transform: `scale(${scale}) translateX(${shift}px)`,
                    letterSpacing: 8,
                }}
            >
                {brandText}
            </h1>
        </div>
    );
};
""",
    ),
]

MANIM_TEMPLATES = [
    (
        "Create a Manim scene animating an autonomous DarkFactory cyber monolith with glowing vector lines.",
        """from manim import *


class DarkFactoryCyberMonolithScene(Scene):
    def construct(self):
        self.camera.background_color = "#0a0a0c"

        monolith = Rectangle(width=2.5, height=5.0, color="#00ffcc", fill_opacity=0.15)
        title = Text("DARKFACTORY CORE", font="Monospace", color="#ffffff").scale(0.8)
        title.next_to(monolith, DOWN, buff=0.6)

        self.play(DrawBorderThenFill(monolith), run_time=1.8)
        self.play(FadeIn(title, shift=UP * 0.5), run_time=1.0)
        self.wait(1.5)
""",
    ),
    (
        "Generate a Manim scene rendering a high-density neural telemetry matrix.",
        """from manim import *


class DarkFactoryTelemetryMatrixScene(Scene):
    def construct(self):
        self.camera.background_color = "#000000"

        grid = NumberPlane(
            x_range=[-5, 5, 1],
            y_range=[-3, 3, 1],
            background_line_style={"stroke_color": "#112233", "stroke_width": 1},
        )
        nodes = VGroup(*[
            Dot(point=[x, y, 0], color="#00ffaa", radius=0.06)
            for x in range(-4, 5, 2)
            for y in range(-2, 3, 2)
        ])

        self.play(Create(grid), run_time=1.5)
        self.play(Create(nodes), run_time=1.2)
        self.wait(1)
""",
    ),
    (
        "Animate algorithmic flow chart transition in Manim with industrial cyber aesthetics.",
        """from manim import *


class DarkFactoryPipelineScene(Scene):
    def construct(self):
        self.camera.background_color = "#050508"

        box_a = Square(side_length=1.5, color="#ff0055")
        box_b = Square(side_length=1.5, color="#00e5ff").shift(RIGHT * 3.5)
        arrow = Arrow(box_a.get_right(), box_b.get_left(), color="#ffffff")

        self.play(FadeIn(box_a), FadeIn(box_b), GrowArrow(arrow), run_time=1.5)
        self.wait(1)
""",
    ),
]

BLENDER_TEMPLATES = [
    (
        "Write a Python script for Blender setting up an industrial DarkFactory scene with cinematic lighting and obsidian shaders.",
        """import bpy


def setup_darkfactory_environment():
    # Purge existing scene mesh objects
    bpy.ops.object.select_all(action="DESELECT")

    # Configure cinematic camera
    cam_data = bpy.data.cameras.new("CyberIndustrialCam")
    cam_data.lens = 45.0
    cam_obj = bpy.data.objects.new("CyberIndustrialCam", cam_data)
    cam_obj.location = (0.0, -6.5, 2.2)
    cam_obj.rotation_euler = (1.25, 0.0, 0.0)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Create dark metallic material
    mat = bpy.data.materials.new(name="ObsidianIndustrial")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.015, 0.015, 0.02, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.95
        bsdf.inputs["Roughness"].default_value = 0.12

    return cam_obj
""",
    ),
    (
        "Set up an autonomous procedural lighting rig in Blender for hardware asset visualization.",
        """import bpy


def create_cyber_lighting_rig():
    bpy.ops.scene.new(type="NEW")

    # Key light setup
    key_light_data = bpy.data.lights.new(name="KeyLight", type="AREA")
    key_light_data.energy = 450.0
    key_light_data.color = (0.0, 0.9, 1.0)
    key_light = bpy.data.objects.new(name="KeyLight", object_data=key_light_data)
    key_light.location = (3.0, -4.0, 4.0)
    bpy.context.collection.objects.link(key_light)

    # Rim camera and material config
    cam_data = bpy.data.cameras.new(name="StudioCamera")
    cam_obj = bpy.data.objects.new(name="StudioCamera", object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    return key_light
""",
    ),
    (
        "Procedurally assemble a futuristic chassis frame with material and camera bindings in Blender.",
        """import bpy


def build_procedural_chassis():
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 1))
    cube = bpy.context.active_object
    cube.name = "ChassisCore"

    mat = bpy.data.materials.new(name="ChassisMaterial")
    cube.data.materials.append(mat)

    cam_data = bpy.data.cameras.new(name="MainChassisCamera")
    cam_obj = bpy.data.objects.new(name="MainChassisCamera", object_data=cam_data)
    bpy.context.collection.objects.link(cam_obj)

    return cube
""",
    ),
]

TOOL_CALLING_TEMPLATES = [
    (
        "Dispatch rendering job for a 4K 60fps DarkFactory brand reveal sequence.",
        json.dumps(
            {
                "name": "render_motion_composition",
                "arguments": {
                    "composition_id": "DarkFactoryCyberLowerThird",
                    "resolution": "3840x2160",
                    "fps": 60,
                    "codec": "prores4444",
                    "aesthetic_preset": "darkfactory_cyber_industrial",
                    "parameters": {
                        "primary_color": "#00ffcc",
                        "background_color": "#0a0a0c",
                        "motion_blur": True,
                    },
                },
            },
            indent=2,
        ),
    ),
    (
        "Execute automated AST inspection on newly generated Manim animation scripts.",
        json.dumps(
            {
                "tool": "ast_codebase_validator",
                "arguments": {
                    "target_file": "scenes/darkfactory_monolith.py",
                    "strict_typing": True,
                    "allowed_imports": ["manim", "math", "numpy"],
                    "fail_fast": True,
                },
            },
            indent=2,
        ),
    ),
    (
        "Trigger Blender Cycles headless shot render with multi-pass denoising.",
        json.dumps(
            {
                "name": "blender_render_shot",
                "arguments": {
                    "scene_path": "assets/scenes/darkfactory_rig.blend",
                    "engine": "CYCLES",
                    "samples": 512,
                    "denoising": "OPTIX",
                    "output_path": "exports/frames/shot_01_####.exr",
                },
            },
            indent=2,
        ),
    ),
]


class LoraDatasetGenerator:
    """Generates synthetic LoRA training datasets for DarkFactory generative workflows."""

    def __init__(self, config: LoraDatasetConfig | None = None) -> None:
        self.config = config or LoraDatasetConfig()
        self._counter: dict[LoraDomain, int] = {d: 0 for d in LoraDomain}

    def generate_sample(
        self, domain: LoraDomain, sample_idx: int | None = None
    ) -> LoraTrainingSample:
        """Generates a single synthetic training sample for the specified domain."""
        if sample_idx is None:
            idx = self._counter[domain]
            self._counter[domain] += 1
        else:
            idx = sample_idx

        # Deterministic pseudo-randomness based on seed and sample index
        rng = random.Random(self.config.seed + hash(domain.value) % 10000 + idx)

        sample_id = f"{domain.value.lower()}-{idx:04d}"

        if domain == LoraDomain.MOTION_REMOTION:
            prompt, response = rng.choice(REMOTION_TEMPLATES)
        elif domain == LoraDomain.MOTION_MANIM:
            prompt, response = rng.choice(MANIM_TEMPLATES)
        elif domain == LoraDomain.MOTION_BLENDER:
            prompt, response = rng.choice(BLENDER_TEMPLATES)
        elif domain == LoraDomain.TOOL_CALLING:
            prompt, response = rng.choice(TOOL_CALLING_TEMPLATES)
        else:
            prompt = f"Prompt for {domain.value} index {idx}"
            response = f"Response for {domain.value} index {idx}"

        return LoraTrainingSample(
            id=sample_id,
            domain=domain,
            system_instruction=DARKFACTORY_SYSTEM_INSTRUCTION,
            user_prompt=prompt,
            target_response=response,
            metadata={
                "aesthetic": "darkfactory",
                "seed": self.config.seed,
                "sample_idx": idx,
            },
            is_valid=True,
            syntax_errors=[],
        )

    def generate_dataset(self) -> list[LoraTrainingSample]:
        """Generates a complete dataset according to configured domains and counts."""
        dataset: list[LoraTrainingSample] = []
        for domain in self.config.domains:
            for idx in range(self.config.samples_per_domain):
                sample = self.generate_sample(domain, sample_idx=idx)
                dataset.append(sample)
        return dataset
