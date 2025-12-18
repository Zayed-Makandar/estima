import { useState, MouseEvent, useRef } from "react";
import "../styles.css";

interface ImageMagnifierProps {
    src: string;
    alt: string;
    zoomLevel?: number;
}

export function ImageMagnifier({ src, alt, zoomLevel = 2.5 }: ImageMagnifierProps) {
    const [showMagnifier, setShowMagnifier] = useState(false);
    const [xy, setXY] = useState({ x: 0, y: 0 });
    const [imgSize, setImgSize] = useState({ width: 0, height: 0 });
    const imgRef = useRef<HTMLImageElement>(null);

    const handleMouseEnter = (e: MouseEvent) => {
        const elem = e.currentTarget;
        const { width, height } = elem.getBoundingClientRect();
        setImgSize({ width, height });
        setShowMagnifier(true);
    };

    const handleMouseMove = (e: MouseEvent) => {
        const elem = e.currentTarget;
        const { top, left, width, height } = elem.getBoundingClientRect();
        const x = e.pageX - left - window.scrollX;
        const y = e.pageY - top - window.scrollY;
        setXY({ x, y });
    };

    const handleMouseLeave = () => {
        setShowMagnifier(false);
    };

    return (
        <div
            className="magnifier-container"
            style={{ position: "relative" }}
        >
            <img
                ref={imgRef}
                src={src}
                alt={alt}
                className="magnifier-image"
                onMouseEnter={handleMouseEnter}
                onMouseMove={handleMouseMove}
                onMouseLeave={handleMouseLeave}
            />

            {showMagnifier && (
                <div
                    style={{
                        display: "block",
                        position: "absolute",
                        pointerEvents: "none",
                        height: `${150}px`,
                        width: `${150}px`,
                        top: `${xy.y - 75}px`, // Center lens
                        left: `${xy.x - 75}px`,
                        opacity: "1",
                        border: "1px solid lightgray",
                        backgroundColor: "white",
                        backgroundImage: `url('${src}')`,
                        backgroundRepeat: "no-repeat",
                        // Calculate background size: Original image size * zoom level
                        backgroundSize: `${imgSize.width * zoomLevel}px ${imgSize.height * zoomLevel}px`,
                        // Calculate position: -((CursorX * zoom) - LensHalfWidth)
                        backgroundPositionX: `${-xy.x * zoomLevel + 75}px`,
                        backgroundPositionY: `${-xy.y * zoomLevel + 75}px`,
                        borderRadius: "50%", // Circle lens
                        boxShadow: "0 0 10px rgba(0,0,0,0.25)"
                    }}
                />
            )}
        </div>
    );
}
