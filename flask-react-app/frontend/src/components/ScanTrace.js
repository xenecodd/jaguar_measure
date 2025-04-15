import React, { useState, useEffect, useRef } from "react";
import io from "socket.io-client";
import { API_BASE_URL } from "../constants/api";

function ScanTrace() {
    const [cords, setCords] = useState([3,3]);
    const canvasRef = useRef(null);
    const [socket, setSocket] = useState(null);
    const [vacuum, setVacuum] = useState(1);

    // cords güncellendiğinde canvas'a çizim yap


    useEffect(() => {

        const socketConnection = io(API_BASE_URL, {
            timeout: 5000,       // Connection timeout
            reconnectionAttempts: 5,
            reconnectionDelay: 1000
          });

        setSocket(socketConnection);
        socketConnection.on('robot_status', (data) => {
            setCords([data.TCP[1][0]+500, data.TCP[1][1]+500]);
            setVacuum(data.DI0);
        });
        
    }, []);

    useEffect(() => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");

        if (cords.length === 2 && vacuum === 0) {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.rect(cords[0], cords[1], 20, 20);
            ctx.fillStyle = "yellow";
            ctx.fill();
        }
        else if (vacuum === 1) {
            ctx.clearRect(10, 10, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.rect(cords[0], cords[1], 20, 20);
            ctx.fillStyle = "blue";
            ctx.fill();
        }
    }, [cords]);

    return (
        <div>
            <canvas 
                ref={canvasRef}
                id="myCanvas"
                width="800"
                height="600"
            ></canvas>
            <div>
                {cords[0]} {cords[1]}
            </div>

        </div>
    );
}

export default ScanTrace;
