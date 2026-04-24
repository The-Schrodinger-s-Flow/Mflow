/*
 * Freya Whiteford, University of Glasgow, Apr 2026

 * Filter cube for low-cost confocal, 16mm Thorlabs cage variant
 *
 * Identical optical layout and filter parameters to filter_cube.scad, but
 * resized and re-drilled to fit the Thorlabs SR 16mm cage system:
 *   - 16mm rod spacing (centre-to-centre)
 *   - 4mm diameter cage rods
 *   - M3 clamping set screws
 *
 * Filter dimensions (excitation / emission / dichroic) are unchanged.
 *
 * Optical path:
 * 1. Excitation light enters horizontally through filter
 * 2. Dichroic at 45° reflects light downward toward sample (-Z)
 * 3. Emission light returns upward from sample (+Z)
 * 4. Emission passes through dichroic and exits through filter
 *
 * TODO: rename emission/excitation after rotating cube to match actual beam path
 * Date: 23 Apr 2026
 */


// Filter dimensions (mm) — matched to filter_cube.scad
// Excitation and emission filters are circular
excitation_filter_diameter = 12.7;  // Diameter
excitation_filter_thickness = 5.0;   // Thickness

emission_filter_diameter = 12.7;  // Diameter
emission_filter_thickness = 5.0;   // Thickness

// Dichroic mirror is rectangular
dichroic_width = 18;   // Width (x dimension)
dichroic_height = 12.7;  // Height (y dimension)
dichroic_thickness = 1.5;  // Thickness (typically thinner than filters)

// Cube dimensions — sized to host 16mm cage rods with enough wall thickness
cube_size = 26.0;  // Overall cube size (shrunk from 40.6mm; fits 16mm cage spacing)
wall_thickness = 2.0;  // Wall thickness around filters

// Thorlabs 16mm cage system mounting (SR series)
cage_rod_spacing = 16.0;  // Centre-to-centre distance (Thorlabs 16mm cage standard)
cage_rod_diameter = 4.0;  // 4mm cage rod diameter
cage_rod_hole_diameter = 4.2;  // Slightly larger for clearance

// Cage rod clamping holes (set screws to secure rods) — M3 for 16mm cage
clamp_hole_diameter = 2.5;  // M3 tap drill size
clamp_hole_depth = 6.0;  // Depth of clamping hole (shorter to fit smaller cube)

// Cutout clearance (negative = smaller cutout for friction fit)
filter_clearance = 0.05;
dichroic_clearance = 0.1;  // Slightly looser for delicate dichroic

// Slot depth for filter insertion
filter_slot_depth = 7.0;  // How far filter slides into cube (fits 5mm filter + lip)
dichroic_slot_depth = cube_size/2;  // Dichroic slot depth to centre it in cube

// Retention lip parameters
filter_lip_depth = 0.5;  // Depth of retention lip (how far it protrudes inward)
filter_lip_thickness = 1.0;  // Thickness of lip along insertion axis

// Filter window recess parameters — sized for SM05 (1/2") lens tube compatibility
filter_recess_diameter = 13.3;  // SM05 thread OD clearance
filter_recess_depth = 3.0;  // Shallower recess to suit smaller cube

// Optical path diameter
beam_diameter = 10.0;  // Clear aperture for light path

// Thorlabs post mounting (M4 metric threading) — shorter blind hole for smaller cube
post_mount_hole_diameter = 3.2;  // Drill size for M4 tap (3.3mm standard)
post_mount_depth = 10.0;  // Depth of threaded hole from -Y face
post_mount_position_z = 0;  // Z position of post mount (0 = centred)

// Print tolerances
$fn = 60;  // Smoothness of curved surfaces

// ============================================================================
// DERIVED DIMENSIONS
// ============================================================================

// Calculate positions to centre the optical paths
excitation_offset_z = cube_size / 2;
emission_offset_z = cube_size / 2;
dichroic_offset_z = cube_size / 2;

// ============================================================================
// MAIN ASSEMBLY
// ============================================================================

module filter_cube() {
    difference() {
        // Main cube body
        cube([cube_size, cube_size, cube_size], center=true);

        // Excitation path (along X axis)
        excitation_path();

        // Emission path (along Y axis)
        emission_path();

        // Dichroic slot (45° angle)
        dichroic_slot();

        // Filter insertion slots
        excitation_filter_slot();
        emission_filter_slot();

        // Thorlabs cage rod mounting holes
        cage_rod_holes();

        // Thorlabs post mounting hole (-Y face)
        post_mount_hole();
    }

}

// ============================================================================
// OPTICAL PATHS
// ============================================================================

module excitation_path() {
    // Beam path along X axis (excitation light enters from -X direction)
    // -X face is blocked
    translate([cube_size/4, 0, 0])
        rotate([0, 90, 0])
            cylinder(h=cube_size/2 + 2, d=beam_diameter, center=true);

    // Flared exit for alignment (+X side only)
    translate([cube_size/2 - 1, 0, 0])
        rotate([0, 90, 0])
            cylinder(h=2, d1=beam_diameter, d2=beam_diameter + 4, center=false);
}

module emission_path() {
    // Beam path along Z axis (emission light exits in +Z direction, toward detector)
    // Through hole on both -Z and +Z faces
    cylinder(h=cube_size + 2, d=beam_diameter, center=true);

    // Flared exit at top (+Z)
    translate([0, 0, cube_size/2 - 1])
        cylinder(h=2, d1=beam_diameter, d2=beam_diameter + 4, center=false);

    // Flared entrance at bottom (-Z)
    translate([0, 0, -cube_size/2 - 1])
        cylinder(h=2, d1=beam_diameter + 4, d2=beam_diameter, center=false);
}

// ============================================================================
// FILTER SLOTS
// ============================================================================

module excitation_filter_slot() {
    // Slot for circular excitation filter (normal to X axis)
    // Filter inserted from +X direction
    translate([cube_size/2 - filter_slot_depth/2 + 1, 0, 0]) {
        rotate([0, 90, 0]) {
            // Main slot
            cylinder(h=filter_slot_depth,
                    d=excitation_filter_diameter + filter_clearance,
                    center=true);

            // Retention lip - creates a step for filter to seat against
            // Positioned at the back of the slot (deeper inside)
            translate([0, 0, -filter_slot_depth/2 + excitation_filter_thickness/2])
                cylinder(h=filter_slot_depth - excitation_filter_thickness - filter_lip_thickness,
                        d=excitation_filter_diameter + filter_clearance + filter_lip_depth * 2,
                        center=false);
        }

        // Entry chamfer for easier insertion
        translate([filter_slot_depth/2 - 0.5, 0, 0])
            rotate([0, 90, 0])
                cylinder(h=1,
                        d1=excitation_filter_diameter + 2,
                        d2=excitation_filter_diameter + filter_clearance,
                        center=false);
    }

    // Recess in front of filter window (SM05-compatible)
    translate([cube_size/2 + 1 - filter_recess_depth/2, 0, 0])
        rotate([0, 90, 0])
            cylinder(h=filter_recess_depth, d=filter_recess_diameter, center=true);
}

module emission_filter_slot() {
    // Slot for circular emission filter (normal to Z axis)
    // Filter inserted from +Z direction (top)
    translate([0, 0, cube_size/2 - filter_slot_depth/2 + 1]) {
        // Main slot
        cylinder(h=filter_slot_depth,
                d=emission_filter_diameter + filter_clearance,
                center=true);

        // Retention lip - creates a step for filter to seat against
        // Positioned at the back of the slot (deeper inside)
        translate([0, 0, -filter_slot_depth/2 + emission_filter_thickness/2])
            cylinder(h=filter_slot_depth - emission_filter_thickness - filter_lip_thickness,
                    d=emission_filter_diameter + filter_clearance + filter_lip_depth * 2,
                    center=false);

        // Entry chamfer for easier insertion
        translate([0, 0, filter_slot_depth/2 - 0.5])
            cylinder(h=1,
                    d1=emission_filter_diameter + 2,
                    d2=emission_filter_diameter + filter_clearance,
                    center=false);
    }

    // Recess in front of filter window (SM05-compatible)
    translate([0, 0, cube_size/2 + 1 - filter_recess_depth/2])
        cylinder(h=filter_recess_depth, d=filter_recess_diameter, center=true);
}

module dichroic_slot() {
    // Slot for rectangular dichroic mirror (45° angle in XZ plane)
    // Rotated to intersect excitation (X) and emission (Z) paths
    // Dichroic redirects horizontal excitation light downward to sample
    rotate([0, 45, 0]) {
        // Main slot - extends through the cube at 45° in XZ plane
        cube([
            dichroic_thickness + dichroic_clearance,
            dichroic_width + dichroic_clearance,
            dichroic_height + dichroic_clearance
        ], center=true);
    }

    // Insertion slot from side (+Y direction) for secure placement
    rotate([0, 45, 0])
        translate([0, cube_size/2 - dichroic_slot_depth/2 + 1, 0])
            cube([
                dichroic_thickness + dichroic_clearance,
                dichroic_slot_depth,
                dichroic_height + dichroic_clearance
            ], center=true);

    // Entry chamfer for dichroic from +Y side
    rotate([0, 45, 0])
        translate([0, cube_size/2 - 0.5, 0])
            rotate([90, 0, 0])
                linear_extrude(height=1, scale=0.9)
                    square([dichroic_thickness + 2, dichroic_height + 2], center=true);
}

module mounting_features() {
    // Add mounting holes or dovetail for positioning in microscope
    // Example: Mounting holes at corners
    mounting_hole_offset = cube_size/2 - 5;

    for (x = [-1, 1], y = [-1, 1]) {
        translate([x * mounting_hole_offset, y * mounting_hole_offset, 0])
            cylinder(h=cube_size + 2, d=3.5, center=true);
    }
}

module cage_rod_holes() {
    // Cage rod holes for Thorlabs 16mm cage system in both Z and X directions
    // Holes are positioned 16mm apart (centre-to-centre) in a square pattern
    offset = cage_rod_spacing / 2;

    // Four holes in Z direction (vertical, through top and bottom)
    for (x = [-1, 1], y = [-1, 1]) {
        translate([x * offset, y * offset, 0])
            cylinder(h=cube_size + 2, d=cage_rod_hole_diameter, center=true);

        // Clamping holes perpendicular to Z rods (from +Y and -Y faces)
        for (y_side = [-1, 1]) {
            translate([x * offset, y_side * cube_size/2, y * offset])
                rotate([90, 0, 0])
                    cylinder(h=clamp_hole_depth, d=clamp_hole_diameter, center=false);
        }
    }

    // Four holes in X direction (horizontal, through left and right sides)
    for (y = [-1, 1], z = [-1, 1]) {
        translate([0, y * offset, z * offset])
            rotate([0, 90, 0])
                cylinder(h=cube_size + 2, d=cage_rod_hole_diameter, center=true);

        // Clamping holes perpendicular to X rods (from +Z and -Z faces)
        for (z_side = [-1, 1]) {
            translate([y * offset, y * offset, z_side * cube_size/2])
                cylinder(h=clamp_hole_depth, d=clamp_hole_diameter, center=false);
        }
    }
}

module post_mount_hole() {
    // Female threaded hole for M4 post mounting
    // Positioned on -Y face, centred in X, at specified Z position
    translate([0, -cube_size/2 + 5, post_mount_position_z])
        rotate([90, 0, 0])
            cylinder(h=post_mount_depth, d=post_mount_hole_diameter, center=false);
}

// ============================================================================
// VISUALISATION HELPERS
// ============================================================================

module show_filters() {
    // Visualize filter positions (for design validation)
    // Excitation filter - circular (green) - horizontal on X axis
    color("green", 0.5)
        translate([cube_size/2 - filter_slot_depth + excitation_filter_thickness/2, 0, 0])
            rotate([0, 90, 0])
                cylinder(h=excitation_filter_thickness,
                        d=excitation_filter_diameter,
                        center=true);

    // Emission filter - circular (red) - vertical on Z axis
    color("red", 0.5)
        translate([0, 0, cube_size/2 - filter_slot_depth + emission_filter_thickness/2])
            cylinder(h=emission_filter_thickness,
                    d=emission_filter_diameter,
                    center=true);

    // Dichroic - rectangular (blue) - 45° in XZ plane
    color("blue", 0.5)
        rotate([0, 45, 0])
            cube([dichroic_thickness, dichroic_width, dichroic_height], center=true);
}

module show_light_rays() {
    // Visualize optical paths
    // Excitation ray (cyan) - horizontal along X axis
    color("cyan", 0.8)
        translate([0, 0, 0])
            rotate([0, 90, 0])
                cylinder(h=cube_size * 0.6, d=1, center=true);

    // Reflected excitation ray to sample (cyan) - downward along -Z
    color("cyan", 0.6)
        translate([0, 0, -cube_size * 0.2])
            cylinder(h=cube_size * 0.3, d=1, center=false);

    // Emission ray from sample (yellow) - upward along +Z axis
    color("yellow", 0.8)
        translate([0, 0, 0])
            cylinder(h=cube_size * 0.8, d=1, center=true);
}

// ============================================================================
// RENDER SELECTION
// ============================================================================

// Choose what to render:
render_mode = "cube";  // Options: "cube", "with_filters", "with_rays", "all"

if (render_mode == "cube") {
    filter_cube();
} else if (render_mode == "with_filters") {
    filter_cube();
    show_filters();
} else if (render_mode == "with_rays") {
    filter_cube();
    show_light_rays();
} else if (render_mode == "all") {
    difference() {
        filter_cube();
        //Cut cube in half to see internal structure
        translate([0, -cube_size, -cube_size/2])
            cube([cube_size*2, cube_size*2, cube_size*2], center=true);
    }
    //show_filters();
    show_light_rays();
}
