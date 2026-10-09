import os
import json

with open("app_server.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update process_frame
old_pf = """        # 2. Scoreboard Detection
        sb_crop = None
        conf = 0.0
        bbox = (0, 0, 0, 0)
        
        # If user explicitly pinned scoreboard ROI within TV, use that
        if self.scoreboard_roi is not None and len(self.scoreboard_roi) == 4:
            sx, sy, sw, sh = self.scoreboard_roi
            th, tw = tv_crop.shape[:2]
            if sx + sw <= tw and sy + sh <= th and sw > 10 and sh > 10:
                sb_crop = tv_crop[sy:sy+sh, sx:sx+sw]
                bbox = (sx, sy, sw, sh)
                conf = 0.95
                
        if sb_crop is None:
            sb_crop, bbox, conf = self.reader.detect_and_crop_scoreboard(tv_crop)
            
        self.detected_scoreboard_bbox = bbox if conf >= 0.40 else None
        
        # 3. Read Scoreboard
        if sb_crop is not None and sb_crop.size > 0 and conf >= 0.40:
            reading = self.reader.read(sb_crop)
        else:
            reading = ScoreboardReading(valid=False, overall_confidence=0.0)
            
        self.last_reading = reading
        self.current_state = self.brain.process_reading(reading, simulated_elapsed_real_seconds=elapsed_delta)
        return reading"""

new_pf = """        # 2. Scoreboard Detection & OCR (Throttled for ultra-smooth 30+ FPS video)
        if (now - self.last_ocr_time) >= self.ocr_interval or self.last_reading is None:
            self.last_ocr_time = now
            sb_crop = None
            conf = 0.0
            bbox = (0, 0, 0, 0)
            
            # If user explicitly pinned scoreboard ROI within TV, use that
            if self.scoreboard_roi is not None and len(self.scoreboard_roi) == 4:
                sx, sy, sw, sh = self.scoreboard_roi
                th, tw = tv_crop.shape[:2]
                if sx + sw <= tw and sy + sh <= th and sw > 10 and sh > 10:
                    sb_crop = tv_crop[sy:sy+sh, sx:sx+sw]
                    bbox = (sx, sy, sw, sh)
                    conf = 0.95
                    
            if sb_crop is None:
                sb_crop, bbox, conf = self.reader.detect_and_crop_scoreboard(tv_crop)
                
            self.detected_scoreboard_bbox = bbox if conf >= 0.40 else None
            
            # 3. Read Scoreboard
            if sb_crop is not None and sb_crop.size > 0 and conf >= 0.40:
                reading = self.reader.read(sb_crop)
            else:
                reading = ScoreboardReading(valid=False, overall_confidence=0.0)
                
            self.last_reading = reading
            
            # Temporal state machine & automated game counting
            prev_state = self.current_state
            new_state = self.brain.process_reading(reading, simulated_elapsed_real_seconds=elapsed_delta)
            self.current_state = new_state
            
            # Check for match completion and increment games in database
            brain_games = getattr(self.brain, "games_counted", 0)
            if (prev_state in ("MATCH_IN_PROGRESS", "EXTRA_TIME") and new_state in ("POSSIBLE_RESTART", "WAITING", "EARLY_MATCH")) or (brain_games > self._last_counted_games):
                self._last_counted_games = brain_games
                print(f"[AUTO-COUNT] Game finished on TV {self.tv_id}! Incrementing game count in DB.")
                try:
                    db_manager.add_completed_game(self.tv_id)
                except Exception as e:
                    print(f"[AUTO-COUNT ERROR] TV {self.tv_id}: {e}")
                    
        return self.last_reading or ScoreboardReading(valid=False, overall_confidence=0.0)"""

if old_pf in content:
    content = content.replace(old_pf, new_pf)
    print("1. process_frame updated successfully")
else:
    print("1. process_frame target not found")

# 2. Update _load_tv_channels fallback
old_load = """                    if isinstance(data, list) and len(data) > 0:
                        for item in data:"""

new_load = """                    if isinstance(data, list):
                        loaded = True
                        for item in data:"""

if old_load in content:
    content = content.replace(old_load, new_load)
    print("2. _load_tv_channels updated successfully")
else:
    print("2. _load_tv_channels target not found")

# 3. Update _capture_and_process_loop speed
old_loop = """    def _capture_and_process_loop(self):
        last_t = time.time()
        while self.running:
            time.sleep(0.1)"""

new_loop = """    def _capture_and_process_loop(self):
        last_t = time.time()
        while self.running:
            time.sleep(0.02)"""

if old_loop in content:
    content = content.replace(old_loop, new_loop)
    print("3. _capture_and_process_loop speed updated successfully")
else:
    print("3. _capture_and_process_loop target not found")

# 4. Update generate_full_stream for clean, high-speed 30 FPS stream
old_stream = """def generate_full_stream():
    \"\"\"MJPEG generator for the main camera stream with glowing TV boxes.\"\"\"
    while True:
        time.sleep(0.06)
        if manager.current_raw_frame is None:
            continue
        
        display = manager.current_raw_frame.copy()
        
        # Draw TV ROIs
        with manager.lock:
            for tid, ch in manager.channels.items():
                if ch.roi:
                    x, y, w, h = ch.roi
                    # Glowing border
                    color = (0, 240, 140) if ch.current_state == \"MATCH_IN_PROGRESS\" else (240, 160, 0)
                    cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
                    
                    label = f\"TV {tid}: {ch.name}\"
                    if ch.customer_name:
                        label += f\" ({ch.customer_name})\"
                    
                    # Background tag
                    cv2.rectangle(display, (x, max(0, y - 24)), (x + len(label) * 9 + 10, y), color, -1)
                    cv2.putText(display, label, (x + 5, max(16, y - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (10, 15, 20), 1, cv2.LINE_AA)
                    
                    # Scoreboard box if detected
                    if ch.detected_scoreboard_bbox:
                        bx, by, bw, bh = ch.detected_scoreboard_bbox
                        cv2.rectangle(display, (x + bx, y + by), (x + bx + bw, y + by + bh), (0, 255, 255), 1)

        _, jpeg = cv2.imencode(\".jpg\", display, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b\"--frame\\r\\nContent-Type: image/jpeg\\r\\n\\r\\n\" + jpeg.tobytes() + b\"\\r\\n\")"""

new_stream = """def generate_full_stream():
    \"\"\"MJPEG generator for the main camera stream: clean, ultra-low latency, 30+ FPS.\"\"\"
    while True:
        time.sleep(0.025)
        if manager.current_raw_frame is None:
            continue
        
        display = manager.current_raw_frame
        h, w = display.shape[:2]
        # Fast downscale if 1080p+ for instant JPEG encoding and low Wi-Fi latency
        if w > 1280:
            scale = 1280.0 / w
            display = cv2.resize(display, (1280, int(h * scale)), interpolation=cv2.INTER_LINEAR)

        _, jpeg = cv2.imencode(\".jpg\", display, [cv2.IMWRITE_JPEG_QUALITY, 70])
        yield (b\"--frame\\r\\nContent-Type: image/jpeg\\r\\n\\r\\n\" + jpeg.tobytes() + b\"\\r\\n\")"""

if old_stream in content:
    content = content.replace(old_stream, new_stream)
    print("4. generate_full_stream updated successfully")
else:
    print("4. generate_full_stream target not found")

# 5. Update auto_detect_tv_screens for smaller TVs and non-overlapping defaults
old_detect = """        min_area = (fw * fh) * 0.04

        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            x, y, w, h = cv2.boundingRect(c)
            aspect = float(w) / max(1, h)
            if 1.1 <= aspect <= 2.4 and w >= 200 and h >= 120:"""

new_detect = """        min_area = (fw * fh) * 0.008

        for c in contours:
            area = cv2.contourArea(c)
            if area < min_area:
                continue
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            x, y, w, h = cv2.boundingRect(c)
            aspect = float(w) / max(1, h)
            if 1.0 <= aspect <= 2.6 and w >= 80 and h >= 45:"""

if old_detect in content:
    content = content.replace(old_detect, new_detect)
    print("5. auto_detect_tv_screens updated successfully")
else:
    print("5. auto_detect_tv_screens target not found")

# 6. Add new clear_all and auto_apply_all endpoints
old_ep = """@app.route(\"/api/tv/delete/<int:tv_id>\", methods=[\"POST\"])
@require_role(\"OWNER\")
def api_delete_tv(tv_id):
    return jsonify(manager.delete_tv(tv_id))"""

new_ep = """@app.route(\"/api/tv/delete/<int:tv_id>\", methods=[\"POST\"])
@require_role(\"OWNER\")
def api_delete_tv(tv_id):
    return jsonify(manager.delete_tv(tv_id))

@app.route(\"/api/tv/clear_all\", methods=[\"POST\"])
@require_role(\"OWNER\")
def api_clear_all_tvs():
    with manager.lock:
        manager.channels.clear()
        with open(TV_REGIONS_FILE, \"w\") as f:
            json.dump([], f, indent=4)
        try:
            conn = db_manager.get_connection()
            conn.execute(\"DELETE FROM tvs\")
            conn.commit()
            conn.close()
        except Exception:
            pass
    return jsonify({\"success\": True, \"message\": \"All TV calibrations cleared. Clean slate ready!\"})

@app.route(\"/api/calibration/auto_apply_all_tvs\", methods=[\"POST\"])
@require_role(\"OWNER\")
def api_auto_apply_all_tvs():
    scan = manager.auto_detect_tv_screens()
    screens = scan.get(\"detected_screens\") or []
    if not screens:
        return jsonify({\"success\": False, \"message\": \"No screens detected to apply.\"}), 400
    
    with manager.lock:
        manager.channels.clear()
        for idx, s in enumerate(screens, 1):
            tid = idx
            name = f\"TV {tid}\"
            corners = s.get(\"corners\")
            bbox = s.get(\"bounding_box\")
            roi = (bbox[\"x\"], bbox[\"y\"], bbox[\"w\"], bbox[\"h\"]) if bbox else None
            sb_roi = s.get(\"scoreboard_roi\")
            corners_list = [[float(p[0]), float(p[1])] for p in corners] if corners else None
            ch = WebTVChannel(tid, name, \"\", roi, sb_roi, corners_list, enable_anti_glare=True)
            manager.channels[tid] = ch
        manager._save_channels_to_json()
        
    return jsonify({
        \"success\": True, 
        \"count\": len(manager.channels), 
        \"message\": f\"Successfully configured all {len(manager.channels)} TV stations across the room!\"
    })"""

if old_ep in content:
    content = content.replace(old_ep, new_ep)
    print("6. new endpoints added successfully")
else:
    print("6. new endpoints target not found")

with open("app_server.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Finished applying optimizations to app_server.py!")
