pip install aiohttp aiortc opencv-python av

            # Display frame locally
            cv2.imshow("Local Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
