import React, { useEffect, useRef } from "react";

export const ParticleLoader = () => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const requestRef = useRef<number>();
    const timerRef = useRef<number>();

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Configuration matching 47 seconds total
        const TOTAL_DURATION_MS = 47000;
        const UPDATE_INTERVAL = 50;
        const INCREMENT_PER_STEP = (100 / (TOTAL_DURATION_MS / UPDATE_INTERVAL)); // % progrss per step

        let width = 400; // Smaller width
        let height = 200;
        canvas.width = width;
        canvas.height = height;

        // Animation state
        const emitter = {
            h: 50,
            x: width / 2 - 250,
            y: height / 2,
            dx: 0
        };

        let progress = 0;
        let particles: any[] = [];
        let time = 0;

        // Simplex noise implementation (embedded or imported)
        // Simplified noise for particles
        const noise = (x: number, y: number, t: number) => {
            return Math.sin(x * 0.01 + t * 0.01) + Math.cos(y * 0.01 + t * 0.01);
        };

        const draw = () => {
            // Clear completely so the canvas background stays transparent
            ctx.globalCompositeOperation = "source-over";
            ctx.clearRect(0, 0, width, height);
            ctx.globalCompositeOperation = "lighter";

            // Draw Loading Bar
            const barW = 300;
            const barH = emitter.h;
            const barX = width / 2 - barW / 2;
            const barY = emitter.y - emitter.h / 2;

            // Bar fill: completed portion = orange, remaining = white
            const completedWidth = (progress / 100) * barW;
            if (completedWidth > 0) {
                ctx.fillStyle = "#F97300";
                ctx.fillRect(barX, barY, completedWidth, barH);
            }
            if (completedWidth < barW) {
                ctx.fillStyle = "#FFFFFF";
                ctx.fillRect(barX + completedWidth, barY, barW - completedWidth, barH);
            }

            // Bar Border - use black for strong contrast, slightly thicker
            ctx.strokeStyle = "#000000";
            ctx.lineWidth = 4;
            ctx.strokeRect(barX, barY, barW, barH);

            // Progress Text - draw on top in normal blend mode so it's clearly visible
            ctx.globalCompositeOperation = "source-over";
            ctx.font = "700 22px 'Inter', system-ui, -apple-system, sans-serif";
            ctx.fillStyle = "#000000";
            ctx.textAlign = "center";
            ctx.fillText(Math.floor(progress) + "%", width / 2, barY - 10);
            ctx.globalCompositeOperation = "lighter";

            // Fill Bar based on progress? No, script moves emitter
            // The script moves the emitter along the bar
            // Update Emitter position
            const targetX = barX + (progress / 100) * barW;
            if (emitter.x < targetX) {
                emitter.x = targetX;
                emitter.dx = 1; // Moving
            } else {
                emitter.dx = 0;
            }

            // Draw Emitter - same primary orange
            ctx.fillStyle = "#F97300";
            ctx.fillRect(emitter.x, barY, 2, barH);

            // Create particles if moving or random
            if (emitter.dx !== 0 || Math.random() < 0.1) {
                for (let i = 0; i < 2; i++) {
                    particles.push({
                        x: emitter.x,
                        y: emitter.y + (Math.random() * emitter.h - emitter.h / 2),
                        vx: Math.random() * -2,
                        vy: Math.random() - 0.5,
                        r: Math.random() * 2 + 0.5,
                        o: 1,
                        die: time + 50 + Math.random() * 50,
                        green: Math.floor(Math.random() * 100) // Variations of orange/yellow
                    });
                }
            }

            // Update & Draw Particles
            for (let i = particles.length - 1; i >= 0; i--) {
                const p = particles[i];
                if (time > p.die) {
                    particles.splice(i, 1);
                    continue;
                }

                p.x += p.vx;
                p.y += p.vy;
                p.o -= 0.015;

                // Add some noise movement
                p.x += noise(p.x, p.y, time) * 0.5;

                ctx.beginPath();
                // Orange particles: RGB(255, 165, 0) to Red
                ctx.fillStyle = `rgba(255, ${100 + p.green}, 0, ${p.o})`;
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fill();
            }

            time++;
            requestRef.current = requestAnimationFrame(draw);
        };

        // Timer to increment progress linearly over 47s
        const startTime = Date.now();
        const tick = () => {
            const now = Date.now();
            const elapsed = now - startTime;
            const p = Math.min(100, (elapsed / TOTAL_DURATION_MS) * 100);
            progress = p;

            if (p < 100) {
                timerRef.current = setTimeout(tick, UPDATE_INTERVAL) as unknown as number;
            }
        };

        tick();
        requestRef.current = requestAnimationFrame(draw);

        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
            if (timerRef.current) clearTimeout(timerRef.current);
        };

    }, []);

    return (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
            <canvas ref={canvasRef} style={{ maxWidth: "100%", maxHeight: "100px" }} />
        </div>
    );
};
