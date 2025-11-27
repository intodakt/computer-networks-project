# Task Checklist: Room Codes & Auto-Join

- [ ] **Planning**
    - [ ] Create Implementation Plan
    - [ ] Get User Approval (Implicitly given via prompt)

- [ ] **Server Implementation (`whiteboard_server.py`)**
    - [ ] Refactor global `clients` and `drawing_history` into a `Room` class or dictionary structure.
    - [ ] Update `handle_client` to parse `JOIN,Name,RoomCode`.
    - [ ] Update `broadcast` to only send messages to clients in the *same* room.
    - [ ] Implement `CREATE_ROOM` logic (if needed, or just auto-create on join).

- [ ] **Client Implementation (`whiteboard_client.py`)**
    - [ ] Update Start Menu to ask for "Create Room" or "Join Room".
    - [ ] If "Create", generate a random 4-digit code.
    - [ ] If "Join", ask for the code.
    - [ ] Update `JOIN` message to include the Room Code.
    - [ ] Display Room Code in the top corner of the GUI.

- [ ] **Verification**
    - [ ] Verify two clients in the same room can draw together.
    - [ ] Verify two clients in *different* rooms CANNOT see each other.
