// ----------------------------------------------------
// 1. Initialize the 3D Globe
// ----------------------------------------------------
const globeViz = document.getElementById('globe-viz');
const world = Globe()(globeViz)
    .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-water.png')
    .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
    .showGraticules(true)
    .globeMaterial(new THREE.MeshPhongMaterial({ color: '#0a5c5a', transparent: true, opacity: 0.9 }))
    .backgroundColor('rgba(0,0,0,0)')
    .showAtmosphere(true)
    .atmosphereColor('#0a5c5a')
    .atmosphereAltitude(0.15);

// Configure controls
world.controls().autoRotate = true;
world.controls().autoRotateSpeed = 1.5;
world.controls().enableZoom = false;

// Handle window resize for the globe
window.addEventListener('resize', () => {
    world.width(globeViz.clientWidth);
    world.height(globeViz.clientHeight);
});

world.camera().position.z = 300;


// ----------------------------------------------------
// 2. Setup GSAP Animations
// ----------------------------------------------------
gsap.registerPlugin(ScrollTrigger);

// Main timeline pinned to the scroll track
const tl = gsap.timeline({
    scrollTrigger: {
        trigger: "#pin-container",
        pin: true,
        start: "top top",
        end: "+=400%", // 400% of viewport height creates the scroll duration
        scrub: 1, // Smooth scrubbing
    }
});

// Act 1: Dive into the newspaper
tl.to("#newspaper", {
    scale: 30, // massive scale to dive into the page
    opacity: 0,
    duration: 3, 
    ease: "power2.in"
})

// Act 2: Fade in the globe container as we dive
.to("#globe-wrapper", {
    opacity: 1,
    duration: 1
}, "-=1.5") // Start fading in while the newspaper is still zooming

// Shift the camera slightly for a cool 3D effect
.to(world.camera().position, {
    z: 220, // zoom in slightly
    duration: 3
}, "-=1")

// Act 3: Shift the globe to the left and show the subscription form
.to(world.scene().position, {
    x: -150, // shift 3D scene to the left
    duration: 3,
    ease: "power1.inOut"
})
.to("#content-overlay", {
    opacity: 1,
    duration: 2,
    ease: "power2.out",
    onStart: () => {
        document.getElementById('content-overlay').classList.add('active');
    },
    onReverseComplete: () => {
        document.getElementById('content-overlay').classList.remove('active');
    }
}, "-=2.5");

// Animate the subscription box sliding in
tl.fromTo("#subscribe-box", 
    { x: 100 }, 
    { x: 0, duration: 2, ease: "power2.out" },
    "-=2.5"
);
