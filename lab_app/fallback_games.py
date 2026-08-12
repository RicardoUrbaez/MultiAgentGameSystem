from __future__ import annotations

import re
from pathlib import Path


def _title_from_prompt(prompt: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", prompt)
    stop = {
        "a",
        "an",
        "and",
        "build",
        "create",
        "game",
        "make",
        "simple",
        "the",
        "where",
        "with",
    }
    title_words = [word for word in words if word.lower() not in stop][:3]
    return " ".join(title_words).title() or "Arcade Sprint"


def _write_menu(run_path: Path, title: str, instructions: str) -> None:
    scenes_dir = run_path / "src" / "game" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    (scenes_dir / "MenuScene.ts").write_text(
        f"""import {{ Scene }} from 'phaser';

export class MenuScene extends Scene {{
    public constructor() {{
        super('MenuScene');
    }}

    public create(): void {{
        this.cameras.main.setBackgroundColor('#101820');
        const params = new URLSearchParams(window.location.search);
        if (params.get('autostart') === '1') {{
            this.scene.start('GameScene');
            return;
        }}

        this.add.text(512, 235, {title!r}, {{
            fontFamily: 'Trebuchet MS', fontSize: '54px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.add.text(512, 325, {instructions!r}, {{
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#7dd3fc'
        }}).setOrigin(0.5);
        this.add.text(512, 420, 'Press Space or click to start', {{
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#facc15'
        }}).setOrigin(0.5);

        this.input.once('pointerdown', () => this.scene.start('GameScene'));
        this.input.keyboard?.once('keydown-SPACE', () => this.scene.start('GameScene'));
    }}
}}
""",
        encoding="utf-8",
    )


def write_prompt_game(run_path: Path, prompt: str) -> None:
    """Write a reliable prompt-themed Phaser MVP if the ADK output fails."""
    lower = prompt.lower()
    if any(keyword in lower for keyword in ["snake", "worm"]):
        write_snake_game(run_path, prompt)
        return
    if any(keyword in lower for keyword in ["platform", "runner", "jump", "dino", "mario"]):
        write_platform_runner_game(run_path, prompt)
        return
    if any(keyword in lower for keyword in ["flappy", "bird", "fly", "flying"]):
        write_flappy_game(run_path, prompt)
        return
    if any(keyword in lower for keyword in ["car", "traffic", "dodg", "race"]):
        write_polished_car_dodger_game(run_path)
        return
    if any(keyword in lower for keyword in ["space", "alien", "shoot", "laser"]):
        write_space_shooter_game(run_path, prompt)
        return
    if any(keyword in lower for keyword in ["pong", "paddle", "tennis"]):
        write_pong_game(run_path, prompt)
        return
    if any(keyword in lower for keyword in ["maze", "key", "escape", "trap", "exit"]):
        write_maze_game(run_path, prompt)
        return
    write_collect_dodge_game(run_path, prompt)


def write_snake_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt)
    _write_menu(run_path, title, "Guide the snake, eat food, avoid walls and yourself.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        f"""import {{ GameObjects, Math as PhaserMath, Scene }} from 'phaser';

type Cell = {{ x: number; y: number }};

export class GameScene extends Scene {{
    private readonly tile = 28;
    private readonly cols = 28;
    private readonly rows = 20;
    private readonly originX = 120;
    private readonly originY = 104;
    private snake: Cell[] = [{{ x: 8, y: 10 }}, {{ x: 7, y: 10 }}, {{ x: 6, y: 10 }}];
    private direction: Cell = {{ x: 1, y: 0 }};
    private nextDirection: Cell = {{ x: 1, y: 0 }};
    private food: Cell = {{ x: 18, y: 10 }};
    private parts: GameObjects.Rectangle[] = [];
    private foodShape!: GameObjects.Star;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private tick = 0;
    private score = 0;
    private gameOver = false;
    private winner: string | null = null;
    private errors: string[] = [];

    public constructor() {{
        super('GameScene');
    }}

    public create(): void {{
        window.onerror = (message) => this.errors.push(String(message));
        window.addEventListener('unhandledrejection', (event) => this.errors.push(String(event.reason)));
        this.cameras.main.setBackgroundColor('#07111f');
        this.add.rectangle(512, 384, 850, 650, 0x10233a).setStrokeStyle(4, 0x38bdf8);
        this.add.grid(512, 384, 784, 560, this.tile, this.tile, 0x122945, 1, 0x24425f, 0.65);
        this.add.text(512, 42, {title!r}, {{
            fontFamily: 'Trebuchet MS', fontSize: '32px', color: '#e0f2fe', stroke: '#020617', strokeThickness: 5
        }}).setOrigin(0.5);
        this.scoreText = this.add.text(34, 24, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '23px', color: '#f8fafc'
        }});
        this.statusText = this.add.text(34, 56, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '17px', color: '#86efac'
        }});
        this.foodShape = this.add.star(0, 0, 5, 9, 20, 0xfacc15).setStrokeStyle(2, 0xfef3c7);
        this.input.keyboard?.on('keydown-UP', () => this.queueDirection(0, -1));
        this.input.keyboard?.on('keydown-W', () => this.queueDirection(0, -1));
        this.input.keyboard?.on('keydown-DOWN', () => this.queueDirection(0, 1));
        this.input.keyboard?.on('keydown-S', () => this.queueDirection(0, 1));
        this.input.keyboard?.on('keydown-LEFT', () => this.queueDirection(-1, 0));
        this.input.keyboard?.on('keydown-A', () => this.queueDirection(-1, 0));
        this.input.keyboard?.on('keydown-RIGHT', () => this.queueDirection(1, 0));
        this.input.keyboard?.on('keydown-D', () => this.queueDirection(1, 0));
        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.installTestBridge();
        this.render();
    }}

    public update(_time: number, delta: number): void {{
        if (this.gameOver) return;
        this.tick += delta;
        if (this.tick < 120) return;
        this.tick = 0;
        this.direction = this.nextDirection;
        const head = this.snake[0];
        const next = {{ x: head.x + this.direction.x, y: head.y + this.direction.y }};
        if (next.x < 0 || next.x >= this.cols || next.y < 0 || next.y >= this.rows || this.snake.some((part) => part.x === next.x && part.y === next.y)) {{
            this.finish('Game over');
            return;
        }}
        this.snake.unshift(next);
        if (next.x === this.food.x && next.y === this.food.y) {{
            this.score += 1;
            if (this.score >= 12) {{
                this.finish('Victory');
            }} else {{
                this.placeFood();
            }}
        }} else {{
            this.snake.pop();
        }}
        this.render();
    }}

    private queueDirection(x: number, y: number): void {{
        if (this.direction.x + x === 0 && this.direction.y + y === 0) return;
        this.nextDirection = {{ x, y }};
    }}

    private placeFood(): void {{
        do {{
            this.food = {{ x: PhaserMath.Between(0, this.cols - 1), y: PhaserMath.Between(0, this.rows - 1) }};
        }} while (this.snake.some((part) => part.x === this.food.x && part.y === this.food.y));
    }}

    private toWorld(cell: Cell): Cell {{
        return {{ x: this.originX + cell.x * this.tile, y: this.originY + cell.y * this.tile }};
    }}

    private render(): void {{
        for (const part of this.parts) part.destroy();
        this.parts = this.snake.map((cell, index) => {{
            const point = this.toWorld(cell);
            return this.add.rectangle(point.x, point.y, this.tile - 4, this.tile - 4, index === 0 ? 0x38bdf8 : 0x22c55e)
                .setStrokeStyle(2, 0x052e16);
        }});
        const foodPoint = this.toWorld(this.food);
        this.foodShape.setPosition(foodPoint.x, foodPoint.y);
        this.refreshHud();
    }}

    private finish(message: string): void {{
        this.gameOver = true;
        this.winner = message;
        this.add.rectangle(512, 384, 430, 190, 0x020617, 0.86).setStrokeStyle(2, 0xfacc15);
        this.add.text(512, 350, message.toUpperCase(), {{
            fontFamily: 'Trebuchet MS', fontSize: '48px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.add.text(512, 420, 'Press R to restart', {{
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#facc15'
        }}).setOrigin(0.5);
    }}

    private reset(): void {{
        this.scene.restart();
    }}

    private refreshHud(): void {{
        this.scoreText.setText(`Score ${{this.score}}   Length ${{this.snake.length}}`);
        this.statusText.setText(this.gameOver ? 'Finished - press R to restart' : 'Eat stars. Do not hit walls or yourself.');
    }}

    private installTestBridge(): void {{
        window.__GAME_TEST__ = {{
            errors: this.errors,
            getState: () => ({{
                score: this.score,
                length: this.snake.length,
                gameOver: this.gameOver,
                winner: this.winner,
                player: this.snake[0],
                goalCount: 1,
                enemyCount: this.snake.length
            }}),
            reset: () => this.reset(),
            getErrors: () => this.errors
        }};
    }}
}}
""",
        encoding="utf-8",
    )


def write_platform_runner_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt)
    _write_menu(run_path, title, "Jump over hazards, collect coins, and survive the run.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        f"""import {{ GameObjects, Geom, Math as PhaserMath, Scene }} from 'phaser';

type Obstacle = {{ body: GameObjects.Rectangle; kind: 'coin' | 'hazard'; speed: number }};

export class GameScene extends Scene {{
    private player!: GameObjects.Container;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private obstacles: Obstacle[] = [];
    private groundY = 642;
    private velocityY = 0;
    private spawnTimer = 0;
    private score = 0;
    private lives = 3;
    private distance = 0;
    private gameOver = false;
    private winner: string | null = null;
    private errors: string[] = [];

    public constructor() {{
        super('GameScene');
    }}

    public create(): void {{
        window.onerror = (message) => this.errors.push(String(message));
        window.addEventListener('unhandledrejection', (event) => this.errors.push(String(event.reason)));
        this.drawWorld();
        this.player = this.createRunner(190, this.groundY - 48);
        this.scoreText = this.add.text(28, 22, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '23px', color: '#f8fafc', stroke: '#020617', strokeThickness: 4
        }});
        this.statusText = this.add.text(28, 56, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '17px', color: '#bae6fd', stroke: '#020617', strokeThickness: 4
        }});
        this.input.keyboard?.on('keydown-SPACE', () => this.jump());
        this.input.keyboard?.on('keydown-UP', () => this.jump());
        this.input.keyboard?.on('keydown-W', () => this.jump());
        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.input.on('pointerdown', () => this.jump());
        this.installTestBridge();
        this.refreshHud();
    }}

    public update(_time: number, delta: number): void {{
        if (this.gameOver) return;
        this.distance += delta * 0.04;
        this.velocityY += 0.0018 * delta;
        this.player.y = Math.min(this.groundY - 48, this.player.y + this.velocityY * delta);
        if (this.player.y >= this.groundY - 48) this.velocityY = 0;

        this.spawnTimer += delta;
        if (this.spawnTimer > 720) {{
            this.spawnObstacle();
            this.spawnTimer = 0;
        }}

        for (let index = this.obstacles.length - 1; index >= 0; index -= 1) {{
            const obstacle = this.obstacles[index];
            obstacle.body.x -= obstacle.speed * delta / 1000;
            if (obstacle.body.x < -50) {{
                obstacle.body.destroy();
                this.obstacles.splice(index, 1);
                continue;
            }}
            if (Geom.Intersects.RectangleToRectangle(this.player.getBounds(), obstacle.body.getBounds())) {{
                if (obstacle.kind === 'coin') {{
                    this.score += 1;
                    obstacle.body.destroy();
                    this.obstacles.splice(index, 1);
                    if (this.score >= 10) this.finish('Victory');
                }} else {{
                    this.lives -= 1;
                    obstacle.body.destroy();
                    this.obstacles.splice(index, 1);
                    this.cameras.main.shake(120, 0.01);
                    if (this.lives <= 0) this.finish('Game over');
                }}
            }}
        }}
        this.refreshHud();
    }}

    private drawWorld(): void {{
        this.cameras.main.setBackgroundColor('#1d4ed8');
        this.add.rectangle(512, 675, 1024, 190, 0x166534);
        this.add.rectangle(512, this.groundY + 10, 1024, 42, 0x713f12);
        for (const x of [120, 360, 690, 910]) {{
            this.add.ellipse(x, 150 + (x % 2) * 25, 160, 45, 0xffffff, 0.75);
        }}
        this.add.text(512, 38, {title!r}, {{
            fontFamily: 'Trebuchet MS', fontSize: '32px', color: '#f8fafc', stroke: '#082f49', strokeThickness: 5
        }}).setOrigin(0.5);
    }}

    private createRunner(x: number, y: number): GameObjects.Container {{
        const root = this.add.container(x, y);
        root.add([
            this.add.ellipse(0, 8, 52, 58, 0x38bdf8).setStrokeStyle(3, 0x082f49),
            this.add.circle(12, -18, 16, 0xfef3c7).setStrokeStyle(3, 0x082f49),
            this.add.rectangle(-16, 38, 12, 30, 0x0f172a),
            this.add.rectangle(16, 38, 12, 30, 0x0f172a),
            this.add.circle(17, -20, 3, 0x111827)
        ]);
        return root;
    }}

    private jump(): void {{
        if (this.gameOver) {{
            this.reset();
            return;
        }}
        if (this.player.y >= this.groundY - 50) {{
            this.velocityY = -0.72;
        }}
    }}

    private spawnObstacle(): void {{
        const isCoin = PhaserMath.Between(0, 100) < 45;
        if (isCoin) {{
            const coin = this.add.rectangle(1050, PhaserMath.Between(390, 530), 34, 34, 0xfacc15).setStrokeStyle(3, 0xfef3c7);
            this.obstacles.push({{ body: coin, kind: 'coin', speed: 280 }});
        }} else {{
            const hazard = this.add.rectangle(1050, this.groundY - 28, 48, 56, 0xef4444).setStrokeStyle(3, 0x7f1d1d);
            this.obstacles.push({{ body: hazard, kind: 'hazard', speed: 330 }});
        }}
    }}

    private finish(message: string): void {{
        this.gameOver = true;
        this.winner = message;
        this.add.rectangle(512, 384, 430, 190, 0x020617, 0.86).setStrokeStyle(2, 0xfacc15);
        this.add.text(512, 350, message.toUpperCase(), {{
            fontFamily: 'Trebuchet MS', fontSize: '48px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.add.text(512, 420, 'Press R or click to restart', {{
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#facc15'
        }}).setOrigin(0.5);
        this.refreshHud();
    }}

    private reset(): void {{
        this.scene.restart();
    }}

    private refreshHud(): void {{
        this.scoreText.setText(`Score ${{this.score}}   Lives ${{this.lives}}   Distance ${{Math.floor(this.distance)}}`);
        this.statusText.setText(this.gameOver ? 'Finished - restart ready' : 'Space/click jumps. Collect coins, avoid red blocks.');
    }}

    private installTestBridge(): void {{
        window.__GAME_TEST__ = {{
            errors: this.errors,
            getState: () => ({{
                score: this.score,
                lives: this.lives,
                distance: Math.floor(this.distance),
                gameOver: this.gameOver,
                winner: this.winner,
                player: {{ x: this.player.x, y: this.player.y }},
                enemyCount: this.obstacles.filter((obstacle) => obstacle.kind === 'hazard').length,
                goalCount: this.obstacles.filter((obstacle) => obstacle.kind === 'coin').length
            }}),
            reset: () => this.reset(),
            getErrors: () => this.errors
        }};
    }}
}}
""",
        encoding="utf-8",
    )


def write_collect_dodge_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt)
    _write_menu(run_path, title, "Move, collect goals, avoid hazards, and reach 10 points.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        f"""import {{ GameObjects, Geom, Math as PhaserMath, Scene }} from 'phaser';

type Actor = {{
    body: GameObjects.Rectangle;
    kind: 'goal' | 'hazard';
    velocityX: number;
    velocityY: number;
}};

export class GameScene extends Scene {{
    private player!: GameObjects.Rectangle;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private actors: Actor[] = [];
    private score = 0;
    private lives = 3;
    private spawnTimer = 0;
    private gameOver = false;
    private winner: string | null = null;
    private errors: string[] = [];

    public constructor() {{
        super('GameScene');
    }}

    public create(): void {{
        window.onerror = (message) => {{
            this.errors.push(String(message));
        }};
        window.addEventListener('unhandledrejection', (event) => {{
            this.errors.push(String(event.reason));
        }});

        this.cameras.main.setBackgroundColor('#111827');
        this.add.grid(512, 384, 1024, 768, 48, 48, 0x172033, 1, 0x334155, 0.5);
        this.add.text(512, 34, {title!r}, {{
            fontFamily: 'Trebuchet MS', fontSize: '30px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.player = this.add.rectangle(512, 610, 54, 54, 0x38bdf8).setStrokeStyle(4, 0xe0f2fe);
        this.scoreText = this.add.text(24, 22, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#f8fafc'
        }});
        this.statusText = this.add.text(24, 54, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '18px', color: '#86efac'
        }});

        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.installTestBridge();
        this.refreshHud();
    }}

    public update(_time: number, delta: number): void {{
        if (this.gameOver) {{
            return;
        }}
        this.movePlayer(delta);
        this.spawnTimer += delta;
        if (this.spawnTimer >= 700) {{
            this.spawnActor();
            this.spawnTimer = 0;
        }}

        for (let index = this.actors.length - 1; index >= 0; index -= 1) {{
            const actor = this.actors[index];
            actor.body.x += actor.velocityX * delta / 1000;
            actor.body.y += actor.velocityY * delta / 1000;
            if (actor.body.x < 20 || actor.body.x > 1004) {{
                actor.velocityX *= -1;
            }}
            if (actor.body.y > 820) {{
                actor.body.destroy();
                this.actors.splice(index, 1);
                continue;
            }}
            if (Geom.Intersects.RectangleToRectangle(this.player.getBounds(), actor.body.getBounds())) {{
                if (actor.kind === 'goal') {{
                    this.score += 1;
                    actor.body.destroy();
                    this.actors.splice(index, 1);
                    if (this.score >= 10) {{
                        this.finish('You win');
                    }}
                }} else {{
                    this.lives -= 1;
                    actor.body.destroy();
                    this.actors.splice(index, 1);
                    this.cameras.main.shake(120, 0.01);
                    if (this.lives <= 0) {{
                        this.finish('Game over');
                    }}
                }}
            }}
        }}
        this.refreshHud();
    }}

    private movePlayer(delta: number): void {{
        const keyboard = this.input.keyboard;
        if (!keyboard) {{
            return;
        }}
        const speed = 360 * delta / 1000;
        let dx = 0;
        let dy = 0;
        if (keyboard.addKey('LEFT').isDown || keyboard.addKey('A').isDown) dx -= speed;
        if (keyboard.addKey('RIGHT').isDown || keyboard.addKey('D').isDown) dx += speed;
        if (keyboard.addKey('UP').isDown || keyboard.addKey('W').isDown) dy -= speed;
        if (keyboard.addKey('DOWN').isDown || keyboard.addKey('S').isDown) dy += speed;
        this.player.x = PhaserMath.Clamp(this.player.x + dx, 34, 990);
        this.player.y = PhaserMath.Clamp(this.player.y + dy, 100, 720);
    }}

    private spawnActor(): void {{
        const kind = PhaserMath.Between(0, 100) < 62 ? 'goal' : 'hazard';
        const color = kind === 'goal' ? 0x22c55e : 0xef4444;
        const body = this.add.rectangle(PhaserMath.Between(80, 944), -30, 42, 42, color)
            .setStrokeStyle(3, 0x0f172a);
        this.actors.push({{
            body,
            kind,
            velocityX: PhaserMath.Between(-90, 90),
            velocityY: PhaserMath.Between(150, 260)
        }});
    }}

    private finish(message: string): void {{
        this.gameOver = true;
        this.winner = message;
        this.add.text(512, 340, message.toUpperCase(), {{
            fontFamily: 'Trebuchet MS', fontSize: '58px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.add.text(512, 420, 'Press R to restart', {{
            fontFamily: 'Trebuchet MS', fontSize: '24px', color: '#facc15'
        }}).setOrigin(0.5);
        this.refreshHud();
    }}

    private reset(): void {{
        this.score = 0;
        this.lives = 3;
        this.spawnTimer = 0;
        this.gameOver = false;
        this.winner = null;
        this.player.setPosition(512, 610);
        for (const actor of this.actors) {{
            actor.body.destroy();
        }}
        this.actors = [];
        this.scene.restart();
    }}

    private refreshHud(): void {{
        this.scoreText.setText(`Score ${{this.score}}   Lives ${{this.lives}}`);
        this.statusText.setText(this.gameOver ? 'Finished - press R to restart' : 'Collect green goals. Avoid red hazards.');
    }}

    private installTestBridge(): void {{
        window.__GAME_TEST__ = {{
            errors: this.errors,
            getState: () => ({{
                score: this.score,
                lives: this.lives,
                gameOver: this.gameOver,
                winner: this.winner,
                player: {{ x: this.player.x, y: this.player.y }},
                enemyCount: this.actors.filter((actor) => actor.kind === 'hazard').length,
                goalCount: this.actors.filter((actor) => actor.kind === 'goal').length
            }}),
            reset: () => this.reset(),
            getErrors: () => this.errors
        }};
    }}
}}
""",
        encoding="utf-8",
    )


def write_space_shooter_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt)
    _write_menu(run_path, title, "Move left/right, press Space to shoot, clear 10 enemies.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        f"""import {{ GameObjects, Geom, Math as PhaserMath, Scene }} from 'phaser';

export class GameScene extends Scene {{
    private player!: GameObjects.Triangle;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private bullets: GameObjects.Rectangle[] = [];
    private enemies: GameObjects.Rectangle[] = [];
    private score = 0;
    private lives = 3;
    private spawnTimer = 0;
    private shotCooldown = 0;
    private gameOver = false;
    private winner: string | null = null;
    private errors: string[] = [];

    public constructor() {{
        super('GameScene');
    }}

    public create(): void {{
        window.onerror = (message) => this.errors.push(String(message));
        window.addEventListener('unhandledrejection', (event) => this.errors.push(String(event.reason)));
        this.cameras.main.setBackgroundColor('#020617');
        for (let i = 0; i < 80; i += 1) {{
            this.add.circle(PhaserMath.Between(0, 1024), PhaserMath.Between(0, 768), PhaserMath.Between(1, 2), 0xe0f2fe, 0.75);
        }}
        this.add.text(512, 28, {title!r}, {{
            fontFamily: 'Trebuchet MS', fontSize: '30px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.player = this.add.triangle(512, 680, 0, 60, 32, 0, 64, 60, 0x38bdf8)
            .setStrokeStyle(3, 0xe0f2fe);
        this.scoreText = this.add.text(24, 22, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#f8fafc'
        }});
        this.statusText = this.add.text(24, 54, '', {{
            fontFamily: 'Trebuchet MS', fontSize: '18px', color: '#86efac'
        }});
        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.installTestBridge();
        this.refreshHud();
    }}

    public update(_time: number, delta: number): void {{
        if (this.gameOver) return;
        this.movePlayer(delta);
        this.shotCooldown = Math.max(0, this.shotCooldown - delta);
        this.spawnTimer += delta;
        if (this.spawnTimer >= 780) {{
            this.spawnEnemy();
            this.spawnTimer = 0;
        }}

        for (let index = this.bullets.length - 1; index >= 0; index -= 1) {{
            const bullet = this.bullets[index];
            bullet.y -= 560 * delta / 1000;
            if (bullet.y < -20) {{
                bullet.destroy();
                this.bullets.splice(index, 1);
            }}
        }}

        for (let enemyIndex = this.enemies.length - 1; enemyIndex >= 0; enemyIndex -= 1) {{
            const enemy = this.enemies[enemyIndex];
            enemy.y += 160 * delta / 1000;
            if (enemy.y > 820) {{
                enemy.destroy();
                this.enemies.splice(enemyIndex, 1);
                this.lives -= 1;
                if (this.lives <= 0) this.finish('Game over');
                continue;
            }}
            if (Geom.Intersects.RectangleToRectangle(this.player.getBounds(), enemy.getBounds())) {{
                this.finish('Game over');
                continue;
            }}
            for (let bulletIndex = this.bullets.length - 1; bulletIndex >= 0; bulletIndex -= 1) {{
                const bullet = this.bullets[bulletIndex];
                if (Geom.Intersects.RectangleToRectangle(bullet.getBounds(), enemy.getBounds())) {{
                    bullet.destroy();
                    enemy.destroy();
                    this.bullets.splice(bulletIndex, 1);
                    this.enemies.splice(enemyIndex, 1);
                    this.score += 1;
                    if (this.score >= 10) this.finish('Victory');
                    break;
                }}
            }}
        }}
        this.refreshHud();
    }}

    private movePlayer(delta: number): void {{
        const keyboard = this.input.keyboard;
        if (!keyboard) return;
        const speed = 420 * delta / 1000;
        if (keyboard.addKey('LEFT').isDown || keyboard.addKey('A').isDown) this.player.x -= speed;
        if (keyboard.addKey('RIGHT').isDown || keyboard.addKey('D').isDown) this.player.x += speed;
        this.player.x = PhaserMath.Clamp(this.player.x, 40, 984);
        if ((keyboard.addKey('SPACE').isDown || keyboard.addKey('UP').isDown) && this.shotCooldown === 0) {{
            this.bullets.push(this.add.rectangle(this.player.x, this.player.y - 44, 8, 24, 0xfacc15));
            this.shotCooldown = 190;
        }}
    }}

    private spawnEnemy(): void {{
        this.enemies.push(this.add.rectangle(PhaserMath.Between(80, 944), -40, 56, 42, 0xef4444).setStrokeStyle(3, 0xfecaca));
    }}

    private finish(message: string): void {{
        this.gameOver = true;
        this.winner = message;
        this.add.text(512, 340, message.toUpperCase(), {{
            fontFamily: 'Trebuchet MS', fontSize: '58px', color: '#f8fafc'
        }}).setOrigin(0.5);
        this.add.text(512, 420, 'Press R to restart', {{
            fontFamily: 'Trebuchet MS', fontSize: '24px', color: '#facc15'
        }}).setOrigin(0.5);
        this.refreshHud();
    }}

    private reset(): void {{
        this.scene.restart();
    }}

    private refreshHud(): void {{
        this.scoreText.setText(`Score ${{this.score}}   Lives ${{this.lives}}`);
        this.statusText.setText(this.gameOver ? 'Finished - press R to restart' : 'Space fires. Stop enemies before they pass.');
    }}

    private installTestBridge(): void {{
        window.__GAME_TEST__ = {{
            errors: this.errors,
            getState: () => ({{
                score: this.score,
                lives: this.lives,
                gameOver: this.gameOver,
                winner: this.winner,
                player: {{ x: this.player.x, y: this.player.y }},
                bulletCount: this.bullets.length,
                enemyCount: this.enemies.length
            }}),
            reset: () => this.reset(),
            getErrors: () => this.errors
        }};
    }}
}}
""",
        encoding="utf-8",
    )


def write_flappy_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt) or "Flappy Flight"
    _write_menu(run_path, title, "Tap Space or click to flap through the pipes.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        """import { GameObjects, Scene } from 'phaser';

type PipePair = {
    top: GameObjects.Rectangle;
    bottom: GameObjects.Rectangle;
    scored: boolean;
};

export class GameScene extends Scene {
    private bird!: GameObjects.Container;
    private wing!: GameObjects.Ellipse;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private pipes: PipePair[] = [];
    private score = 0;
    private velocity = 0;
    private spawnTimer = 0;
    private gameOver = false;
    private errors: string[] = [];

    public constructor() {
        super('GameScene');
    }

    public create(): void {
        window.onerror = (message) => this.errors.push(String(message));
        window.addEventListener('unhandledrejection', (event) => this.errors.push(String(event.reason)));
        this.drawSky();
        this.bird = this.createBird(260, 350);
        this.scoreText = this.add.text(32, 24, '', {
            fontFamily: 'Trebuchet MS',
            fontSize: '34px',
            color: '#ffffff',
            stroke: '#0f172a',
            strokeThickness: 6
        });
        this.statusText = this.add.text(32, 66, '', {
            fontFamily: 'Trebuchet MS',
            fontSize: '18px',
            color: '#fef3c7',
            stroke: '#0f172a',
            strokeThickness: 4
        });
        this.input.keyboard?.on('keydown-SPACE', () => this.flap());
        this.input.keyboard?.on('keydown-UP', () => this.flap());
        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.input.on('pointerdown', () => this.flap());
        this.installTestBridge();
        this.refreshHud();
    }

    public update(_time: number, delta: number): void {
        if (this.gameOver) {
            return;
        }
        this.velocity += 0.00145 * delta;
        this.bird.y += this.velocity * delta;
        this.bird.angle = Math.max(-18, Math.min(28, this.velocity * 42));
        this.wing.angle = Math.sin(this.time.now / 80) * 18;
        this.spawnTimer += delta;
        if (this.spawnTimer > 1450) {
            this.spawnPipe();
            this.spawnTimer = 0;
        }
        for (let index = this.pipes.length - 1; index >= 0; index -= 1) {
            const pair = this.pipes[index];
            pair.top.x -= delta * 0.19;
            pair.bottom.x -= delta * 0.19;
            if (!pair.scored && pair.top.x < this.bird.x - 24) {
                pair.scored = true;
                this.score += 1;
            }
            if (pair.top.x < -80) {
                pair.top.destroy();
                pair.bottom.destroy();
                this.pipes.splice(index, 1);
                continue;
            }
            if (this.overlapsPipe(pair)) {
                this.endGame();
            }
        }
        if (this.bird.y < 40 || this.bird.y > 718) {
            this.endGame();
        }
        this.refreshHud();
    }

    private drawSky(): void {
        this.cameras.main.setBackgroundColor('#60a5fa');
        this.add.rectangle(512, 720, 1024, 96, 0x22c55e);
        for (const x of [140, 410, 760, 930]) {
            this.add.ellipse(x, 120 + (x % 3) * 22, 150, 48, 0xffffff, 0.82);
        }
        this.add.text(512, 36, 'FLAPPY FLIGHT', {
            fontFamily: 'Trebuchet MS',
            fontSize: '34px',
            color: '#f8fafc',
            stroke: '#1e3a8a',
            strokeThickness: 6
        }).setOrigin(0.5);
    }

    private createBird(x: number, y: number): GameObjects.Container {
        const root = this.add.container(x, y);
        const body = this.add.ellipse(0, 0, 58, 44, 0xfacc15).setStrokeStyle(4, 0x92400e);
        this.wing = this.add.ellipse(-12, 8, 28, 18, 0xf97316).setStrokeStyle(2, 0x9a3412);
        const eye = this.add.circle(14, -10, 6, 0xffffff).setStrokeStyle(2, 0x111827);
        const pupil = this.add.circle(16, -10, 2.5, 0x111827);
        const beak = this.add.triangle(34, 1, 0, 0, 28, 10, 0, 20, 0xfb923c);
        root.add([this.wing, body, eye, pupil, beak]);
        return root;
    }

    private flap(): void {
        if (this.gameOver) {
            this.reset();
            return;
        }
        this.velocity = -0.43;
        this.tweens.add({ targets: this.bird, y: this.bird.y - 6, duration: 70, yoyo: true });
    }

    private spawnPipe(): void {
        const gapCenter = Phaser.Math.Between(190, 540);
        const gapSize = 178;
        const topHeight = gapCenter - gapSize / 2;
        const bottomY = gapCenter + gapSize / 2;
        const bottomHeight = 720 - bottomY;
        const top = this.add.rectangle(1080, topHeight / 2, 78, topHeight, 0x16a34a).setStrokeStyle(4, 0x14532d);
        const bottom = this.add.rectangle(1080, bottomY + bottomHeight / 2, 78, bottomHeight, 0x16a34a).setStrokeStyle(4, 0x14532d);
        this.pipes.push({ top, bottom, scored: false });
    }

    private overlapsPipe(pair: PipePair): boolean {
        const nearX = Math.abs(pair.top.x - this.bird.x) < 58;
        if (!nearX) {
            return false;
        }
        return this.bird.y < pair.top.y + pair.top.height / 2 + 20 || this.bird.y > pair.bottom.y - pair.bottom.height / 2 - 20;
    }

    private endGame(): void {
        this.gameOver = true;
        this.add.rectangle(512, 384, 430, 210, 0x0f172a, 0.84).setStrokeStyle(2, 0xfacc15);
        this.add.text(512, 340, 'GAME OVER', {
            fontFamily: 'Trebuchet MS',
            fontSize: '52px',
            color: '#fecaca'
        }).setOrigin(0.5);
        this.add.text(512, 414, 'Press Space or click to restart', {
            fontFamily: 'Trebuchet MS',
            fontSize: '22px',
            color: '#facc15'
        }).setOrigin(0.5);
        this.refreshHud();
    }

    private reset(): void {
        this.scene.restart();
    }

    private refreshHud(): void {
        this.scoreText.setText(`Score ${this.score}`);
        this.statusText.setText(this.gameOver ? 'Restart ready' : 'Space/click to flap through pipes');
    }

    private installTestBridge(): void {
        window.__GAME_TEST__ = {
            errors: this.errors,
            getState: () => ({
                score: this.score,
                gameOver: this.gameOver,
                birdY: this.bird.y,
                velocity: this.velocity,
                pipeCount: this.pipes.length,
                enemyCount: this.pipes.length
            }),
            reset: () => this.reset(),
            getErrors: () => this.errors
        };
    }
}
""",
        encoding="utf-8",
    )


def write_pong_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt)
    _write_menu(run_path, title, "Move paddles with W/S and Up/Down. First to 5 wins.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        """import { GameObjects, Scene } from 'phaser';

export class GameScene extends Scene {
    private left!: GameObjects.Rectangle;
    private right!: GameObjects.Rectangle;
    private ball!: GameObjects.Arc;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private leftScore = 0;
    private rightScore = 0;
    private ballVelocity = { x: 360, y: 180 };
    private gameOver = false;
    private winner: string | null = null;
    private errors: string[] = [];

    public constructor() {
        super('GameScene');
    }

    public create(): void {
        window.onerror = (message) => this.errors.push(String(message));
        window.addEventListener('unhandledrejection', (event) => this.errors.push(String(event.reason)));
        this.cameras.main.setBackgroundColor('#08111f');
        this.add.rectangle(512, 384, 940, 680, 0x0f172a).setStrokeStyle(4, 0x38bdf8);
        for (let y = 48; y < 720; y += 44) {
            this.add.rectangle(512, y, 8, 24, 0xe0f2fe, 0.5);
        }
        this.left = this.add.rectangle(64, 384, 22, 130, 0x22c55e);
        this.right = this.add.rectangle(960, 384, 22, 130, 0xf97316);
        this.ball = this.add.circle(512, 384, 16, 0xfacc15).setStrokeStyle(3, 0xfef3c7);
        this.scoreText = this.add.text(512, 28, '', {
            fontFamily: 'Trebuchet MS', fontSize: '34px', color: '#f8fafc'
        }).setOrigin(0.5);
        this.statusText = this.add.text(512, 724, '', {
            fontFamily: 'Trebuchet MS', fontSize: '18px', color: '#bae6fd'
        }).setOrigin(0.5);
        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.installTestBridge();
        this.refreshHud();
    }

    public update(_time: number, delta: number): void {
        if (this.gameOver) {
            return;
        }
        this.movePaddles(delta);
        this.ball.x += this.ballVelocity.x * delta / 1000;
        this.ball.y += this.ballVelocity.y * delta / 1000;
        if (this.ball.y < 58 || this.ball.y > 710) {
            this.ballVelocity.y *= -1;
        }
        if (this.hitPaddle(this.left) && this.ballVelocity.x < 0) {
            this.ballVelocity.x = Math.abs(this.ballVelocity.x) + 24;
            this.ballVelocity.y += (this.ball.y - this.left.y) * 4;
        }
        if (this.hitPaddle(this.right) && this.ballVelocity.x > 0) {
            this.ballVelocity.x = -Math.abs(this.ballVelocity.x) - 24;
            this.ballVelocity.y += (this.ball.y - this.right.y) * 4;
        }
        if (this.ball.x < 0) {
            this.rightScore += 1;
            this.serve(-1);
        }
        if (this.ball.x > 1024) {
            this.leftScore += 1;
            this.serve(1);
        }
        if (this.leftScore >= 5 || this.rightScore >= 5) {
            this.gameOver = true;
            this.winner = this.leftScore > this.rightScore ? 'Left player wins' : 'Right player wins';
            this.add.text(512, 338, this.winner.toUpperCase(), {
                fontFamily: 'Trebuchet MS', fontSize: '44px', color: '#f8fafc'
            }).setOrigin(0.5);
            this.add.text(512, 410, 'Press R to restart', {
                fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#facc15'
            }).setOrigin(0.5);
        }
        this.refreshHud();
    }

    private movePaddles(delta: number): void {
        const keyboard = this.input.keyboard;
        if (!keyboard) return;
        const speed = 440 * delta / 1000;
        if (keyboard.addKey('W').isDown) this.left.y -= speed;
        if (keyboard.addKey('S').isDown) this.left.y += speed;
        if (keyboard.addKey('UP').isDown) this.right.y -= speed;
        if (keyboard.addKey('DOWN').isDown) this.right.y += speed;
        this.left.y = PhaserMath.Clamp(this.left.y, 120, 648);
        this.right.y = PhaserMath.Clamp(this.right.y, 120, 648);
    }

    private hitPaddle(paddle: GameObjects.Rectangle): boolean {
        return Math.abs(this.ball.x - paddle.x) < 31 && Math.abs(this.ball.y - paddle.y) < 82;
    }

    private serve(direction: number): void {
        this.ball.setPosition(512, 384);
        this.ballVelocity.x = 360 * direction;
        this.ballVelocity.y = PhaserMath.Between(-220, 220);
    }

    private reset(): void {
        this.scene.restart();
    }

    private refreshHud(): void {
        this.scoreText.setText(`${this.leftScore}  :  ${this.rightScore}`);
        this.statusText.setText(this.gameOver ? 'Match complete' : 'W/S left paddle, Up/Down right paddle');
    }

    private installTestBridge(): void {
        window.__GAME_TEST__ = {
            errors: this.errors,
            getState: () => ({
                leftScore: this.leftScore,
                rightScore: this.rightScore,
                score: this.leftScore + this.rightScore,
                gameOver: this.gameOver,
                winner: this.winner,
                ballX: this.ball.x,
                ballY: this.ball.y,
                leftPaddleY: this.left.y,
                rightPaddleY: this.right.y
            }),
            reset: () => this.reset(),
            getErrors: () => this.errors
        };
    }
}
""",
        encoding="utf-8",
    )


def write_maze_game(run_path: Path, prompt: str) -> None:
    title = _title_from_prompt(prompt)
    _write_menu(run_path, title, "Collect the keys, avoid traps, then reach the exit.")
    scenes_dir = run_path / "src" / "game" / "scenes"
    (scenes_dir / "GameScene.ts").write_text(
        """import { GameObjects, Scene } from 'phaser';

type Cell = { x: number; y: number };

export class GameScene extends Scene {
    private readonly tile = 48;
    private readonly offsetX = 176;
    private readonly offsetY = 72;
    private readonly layout = [
        '##############',
        '#P..#....K...#',
        '#.##.#.####..#',
        '#....#....#..#',
        '####.###..#K.#',
        '#K...#....#..#',
        '#.####.####..#',
        '#......T.....#',
        '#..######.####',
        '#....K....T.E#',
        '##############',
    ];
    private player!: GameObjects.Rectangle;
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private playerCell: Cell = { x: 1, y: 1 };
    private keys = new Set<string>();
    private traps = new Set<string>();
    private exit: Cell = { x: 12, y: 9 };
    private collected = 0;
    private totalKeys = 0;
    private gameOver = false;
    private winner: string | null = null;
    private errors: string[] = [];

    public constructor() {
        super('GameScene');
    }

    public create(): void {
        window.onerror = (message) => this.errors.push(String(message));
        window.addEventListener('unhandledrejection', (event) => this.errors.push(String(event.reason)));
        this.cameras.main.setBackgroundColor('#111827');
        this.drawMaze();
        this.player = this.add.rectangle(0, 0, 30, 30, 0x38bdf8).setStrokeStyle(3, 0xe0f2fe);
        this.placePlayer();
        this.scoreText = this.add.text(28, 22, '', {
            fontFamily: 'Trebuchet MS', fontSize: '24px', color: '#f8fafc'
        });
        this.statusText = this.add.text(28, 54, '', {
            fontFamily: 'Trebuchet MS', fontSize: '18px', color: '#bae6fd'
        });
        this.input.keyboard?.on('keydown-UP', () => this.tryMove(0, -1));
        this.input.keyboard?.on('keydown-W', () => this.tryMove(0, -1));
        this.input.keyboard?.on('keydown-DOWN', () => this.tryMove(0, 1));
        this.input.keyboard?.on('keydown-S', () => this.tryMove(0, 1));
        this.input.keyboard?.on('keydown-LEFT', () => this.tryMove(-1, 0));
        this.input.keyboard?.on('keydown-A', () => this.tryMove(-1, 0));
        this.input.keyboard?.on('keydown-RIGHT', () => this.tryMove(1, 0));
        this.input.keyboard?.on('keydown-D', () => this.tryMove(1, 0));
        this.input.keyboard?.on('keydown-R', () => this.reset());
        this.installTestBridge();
        this.refreshHud();
    }

    private drawMaze(): void {
        this.keys.clear();
        this.traps.clear();
        for (let y = 0; y < this.layout.length; y += 1) {
            for (let x = 0; x < this.layout[y].length; x += 1) {
                const value = this.layout[y][x];
                const px = this.offsetX + x * this.tile;
                const py = this.offsetY + y * this.tile;
                if (value === '#') {
                    this.add.rectangle(px, py, this.tile - 3, this.tile - 3, 0x334155);
                } else {
                    this.add.rectangle(px, py, this.tile - 3, this.tile - 3, 0x172033).setStrokeStyle(1, 0x233044);
                }
                if (value === 'P') this.playerCell = { x, y };
                if (value === 'K') {
                    this.keys.add(`${x},${y}`);
                    this.totalKeys += 1;
                    this.add.star(px, py, 5, 8, 17, 0xfacc15).setStrokeStyle(2, 0xfef3c7);
                }
                if (value === 'T') {
                    this.traps.add(`${x},${y}`);
                    this.add.triangle(px, py + 8, 0, 28, 16, 0, 32, 28, 0xef4444);
                }
                if (value === 'E') {
                    this.exit = { x, y };
                    this.add.rectangle(px, py, 36, 36, 0x22c55e).setStrokeStyle(3, 0xbbf7d0);
                }
            }
        }
    }

    private tryMove(dx: number, dy: number): void {
        if (this.gameOver) return;
        const next = { x: this.playerCell.x + dx, y: this.playerCell.y + dy };
        if (this.layout[next.y]?.[next.x] === '#') return;
        this.playerCell = next;
        this.placePlayer();
        const key = `${next.x},${next.y}`;
        if (this.keys.delete(key)) {
            this.collected += 1;
        }
        if (this.traps.has(key)) {
            this.finish('Game over');
        }
        if (next.x === this.exit.x && next.y === this.exit.y && this.collected >= this.totalKeys) {
            this.finish('Escaped');
        }
        this.refreshHud();
    }

    private placePlayer(): void {
        this.player?.setPosition(this.offsetX + this.playerCell.x * this.tile, this.offsetY + this.playerCell.y * this.tile);
    }

    private finish(message: string): void {
        this.gameOver = true;
        this.winner = message;
        this.add.rectangle(512, 384, 430, 190, 0x020617, 0.86).setStrokeStyle(2, 0x38bdf8);
        this.add.text(512, 350, message.toUpperCase(), {
            fontFamily: 'Trebuchet MS', fontSize: '48px', color: '#f8fafc'
        }).setOrigin(0.5);
        this.add.text(512, 420, 'Press R to restart', {
            fontFamily: 'Trebuchet MS', fontSize: '22px', color: '#facc15'
        }).setOrigin(0.5);
    }

    private reset(): void {
        this.scene.restart();
    }

    private refreshHud(): void {
        this.scoreText.setText(`Keys ${this.collected}/${this.totalKeys}`);
        this.statusText.setText(this.gameOver ? 'Finished' : 'Collect every key before using the green exit');
    }

    private installTestBridge(): void {
        window.__GAME_TEST__ = {
            errors: this.errors,
            getState: () => ({
                score: this.collected,
                keys: this.collected,
                totalKeys: this.totalKeys,
                player: this.playerCell,
                gameOver: this.gameOver,
                winner: this.winner,
                enemyCount: this.traps.size
            }),
            reset: () => this.reset(),
            getErrors: () => this.errors
        };
    }
}
""",
        encoding="utf-8",
    )


def write_car_dodger_game(run_path: Path) -> None:
    scenes_dir = run_path / "src" / "game" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    _write_menu(run_path, "Highway Drift", "Switch lanes, dodge traffic, survive for distance.")
    (scenes_dir / "GameScene.ts").write_text(
        """import { GameObjects, Geom, Math as PhaserMath, Scene } from 'phaser';

type TrafficCar = {
    car: GameObjects.Rectangle;
    lane: number;
    speed: number;
};

export class GameScene extends Scene {
    private readonly laneXs = [372, 512, 652];
    private lane = 1;
    private player!: GameObjects.Rectangle;
    private traffic: TrafficCar[] = [];
    private laneMarkers: GameObjects.Rectangle[] = [];
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private gameOverText?: GameObjects.Text;
    private restartText?: GameObjects.Text;
    private distance = 0;
    private spawnTimer = 0;
    private gameOver = false;
    private errors: string[] = [];

    public constructor() {
        super('GameScene');
    }

    public create(): void {
        window.onerror = (message) => {
            this.errors.push(String(message));
        };
        window.addEventListener('unhandledrejection', (event) => {
            this.errors.push(String(event.reason));
        });

        this.cameras.main.setBackgroundColor('#0f172a');
        this.add.rectangle(512, 384, 420, 768, 0x1f2937);
        this.add.rectangle(300, 384, 14, 768, 0xf8fafc);
        this.add.rectangle(724, 384, 14, 768, 0xf8fafc);

        for (const x of [442, 582]) {
            for (let y = -40; y < 840; y += 96) {
                this.laneMarkers.push(this.add.rectangle(x, y, 8, 48, 0xfacc15));
            }
        }

        this.player = this.add.rectangle(this.laneXs[this.lane], 670, 58, 96, 0x38bdf8)
            .setStrokeStyle(4, 0xe0f2fe);
        this.add.rectangle(this.laneXs[this.lane], 642, 34, 18, 0x0f172a).setName('windshield');

        this.scoreText = this.add.text(28, 24, '', {
            fontFamily: 'Trebuchet MS', fontSize: '24px', color: '#f8fafc'
        });
        this.statusText = this.add.text(28, 58, '', {
            fontFamily: 'Trebuchet MS', fontSize: '18px', color: '#86efac'
        });

        this.input.keyboard?.on('keydown-LEFT', () => this.switchLane(-1));
        this.input.keyboard?.on('keydown-A', () => this.switchLane(-1));
        this.input.keyboard?.on('keydown-RIGHT', () => this.switchLane(1));
        this.input.keyboard?.on('keydown-D', () => this.switchLane(1));
        this.input.keyboard?.on('keydown-R', () => this.reset());

        this.installTestBridge();
        this.refreshHud();
    }

    public update(_time: number, delta: number): void {
        this.scrollRoad(delta);
        if (this.gameOver) {
            return;
        }

        this.distance += delta * 0.045;
        this.spawnTimer += delta;
        if (this.spawnTimer >= 850) {
            this.spawnTraffic();
            this.spawnTimer = 0;
        }

        const speedBoost = Math.min(240, this.distance * 0.12);
        for (let index = this.traffic.length - 1; index >= 0; index -= 1) {
            const item = this.traffic[index];
            item.car.y += (item.speed + speedBoost) * delta / 1000;

            if (item.car.y > 850) {
                item.car.destroy();
                this.traffic.splice(index, 1);
                continue;
            }

            if (Geom.Intersects.RectangleToRectangle(this.player.getBounds(), item.car.getBounds())) {
                this.triggerGameOver();
            }
        }

        this.refreshHud();
    }

    private switchLane(direction: number): void {
        if (this.gameOver) {
            return;
        }
        this.lane = PhaserMath.Clamp(this.lane + direction, 0, this.laneXs.length - 1);
        this.tweens.add({
            targets: this.player,
            x: this.laneXs[this.lane],
            duration: 110,
            ease: 'Quad.easeOut'
        });
    }

    private spawnTraffic(): void {
        const lane = PhaserMath.Between(0, this.laneXs.length - 1);
        const color = PhaserMath.RND.pick([0xef4444, 0xf97316, 0xa855f7, 0x22c55e]);
        const car = this.add.rectangle(this.laneXs[lane], -70, 58, 100, color)
            .setStrokeStyle(4, 0x111827);
        this.traffic.push({ car, lane, speed: PhaserMath.Between(260, 360) });
    }

    private scrollRoad(delta: number): void {
        for (const marker of this.laneMarkers) {
            marker.y += delta * 0.28;
            if (marker.y > 820) {
                marker.y = -50;
            }
        }
    }

    private triggerGameOver(): void {
        this.gameOver = true;
        this.player.setFillStyle(0xf87171);
        this.cameras.main.shake(180, 0.012);
        this.gameOverText = this.add.text(512, 330, 'GAME OVER', {
            fontFamily: 'Trebuchet MS', fontSize: '58px', color: '#fecaca'
        }).setOrigin(0.5);
        this.restartText = this.add.text(512, 410, 'Press R or click to restart', {
            fontFamily: 'Trebuchet MS', fontSize: '24px', color: '#facc15'
        }).setOrigin(0.5).setInteractive({ useHandCursor: true });
        this.restartText.on('pointerdown', () => this.reset());
        this.refreshHud();
    }

    private reset(): void {
        this.distance = 0;
        this.spawnTimer = 0;
        this.gameOver = false;
        this.lane = 1;
        this.player.setPosition(this.laneXs[this.lane], 670).setFillStyle(0x38bdf8);
        for (const item of this.traffic) {
            item.car.destroy();
        }
        this.traffic = [];
        this.gameOverText?.destroy();
        this.restartText?.destroy();
        this.gameOverText = undefined;
        this.restartText = undefined;
        this.refreshHud();
    }

    private refreshHud(): void {
        this.scoreText.setText(`Distance ${Math.floor(this.distance)}m`);
        this.statusText.setText(this.gameOver ? 'Collision detected - restart available' : 'Avoid traffic with Left/Right or A/D');
    }

    private installTestBridge(): void {
        window.__GAME_TEST__ = {
            errors: this.errors,
            getState: () => ({
                score: Math.floor(this.distance),
                distance: Math.floor(this.distance),
                lane: this.lane,
                playerLane: this.lane,
                gameOver: this.gameOver,
                trafficCount: this.traffic.length,
                enemyCount: this.traffic.length
            }),
            reset: () => this.reset(),
            getErrors: () => this.errors
        };
    }
}
""",
        encoding="utf-8",
    )


def write_polished_car_dodger_game(run_path: Path) -> None:
    scenes_dir = run_path / "src" / "game" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    _write_menu(run_path, "Highway Drift", "Switch lanes, dodge traffic, and survive for distance.")
    (scenes_dir / "GameScene.ts").write_text(
        """import { GameObjects, Math as PhaserMath, Scene } from 'phaser';

type TrafficCar = {
    root: GameObjects.Container;
    lane: number;
    speed: number;
};

export class GameScene extends Scene {
    private readonly roadLeft = 300;
    private readonly roadRight = 724;
    private readonly laneXs = [372, 512, 652];
    private playerLane = 1;
    private player!: GameObjects.Container;
    private traffic: TrafficCar[] = [];
    private laneMarkers: GameObjects.Rectangle[] = [];
    private scoreText!: GameObjects.Text;
    private statusText!: GameObjects.Text;
    private distance = 0;
    private spawnTimer = 0;
    private gameOver = false;
    private gameOverLayer?: GameObjects.Container;
    private errors: string[] = [];

    public constructor() {
        super('GameScene');
    }

    public create(): void {
        window.onerror = (message) => {
            this.errors.push(String(message));
        };
        window.addEventListener('unhandledrejection', (event) => {
            this.errors.push(String(event.reason));
        });

        this.drawWorld();
        this.player = this.createCar(this.laneXs[this.playerLane], 660, 0x2dd4bf, 0x042f2e, true);
        this.scoreText = this.add.text(28, 22, '', {
            fontFamily: 'Trebuchet MS',
            fontSize: '24px',
            color: '#f8fafc',
            stroke: '#020617',
            strokeThickness: 5
        });
        this.statusText = this.add.text(28, 56, '', {
            fontFamily: 'Trebuchet MS',
            fontSize: '17px',
            color: '#bae6fd',
            stroke: '#020617',
            strokeThickness: 4
        });

        this.input.keyboard?.on('keydown-LEFT', () => this.switchLane(-1));
        this.input.keyboard?.on('keydown-A', () => this.switchLane(-1));
        this.input.keyboard?.on('keydown-RIGHT', () => this.switchLane(1));
        this.input.keyboard?.on('keydown-D', () => this.switchLane(1));
        this.input.keyboard?.on('keydown-R', () => this.reset());

        this.installTestBridge();
        this.refreshHud();
    }

    public update(_time: number, delta: number): void {
        this.scrollLaneMarkers(delta);
        if (this.gameOver) {
            return;
        }

        this.distance += delta * 0.05;
        this.spawnTimer += delta;
        if (this.spawnTimer >= 780) {
            this.spawnTraffic();
            this.spawnTimer = 0;
        }

        const speedBoost = Math.min(280, this.distance * 0.16);
        for (let index = this.traffic.length - 1; index >= 0; index -= 1) {
            const item = this.traffic[index];
            item.root.y += (item.speed + speedBoost) * delta / 1000;
            if (item.root.y > 860) {
                item.root.destroy();
                this.traffic.splice(index, 1);
                continue;
            }
            if (item.lane === this.playerLane && Math.abs(item.root.y - this.player.y) < 92) {
                this.triggerGameOver();
            }
        }

        this.refreshHud();
    }

    private drawWorld(): void {
        this.cameras.main.setBackgroundColor('#07111f');
        this.add.rectangle(512, 384, 1024, 768, 0x0f3d2e);
        this.add.rectangle(512, 384, 500, 768, 0x111827);
        this.add.rectangle(this.roadLeft, 384, 12, 768, 0xf8fafc);
        this.add.rectangle(this.roadRight, 384, 12, 768, 0xf8fafc);
        this.add.rectangle(512, 384, 430, 768, 0x2b2f36, 0.74);

        for (const x of [442, 582]) {
            for (let y = -40; y < 850; y += 96) {
                this.laneMarkers.push(this.add.rectangle(x, y, 8, 50, 0xfacc15));
            }
        }

        this.add.text(512, 32, 'HIGHWAY DRIFT', {
            fontFamily: 'Trebuchet MS',
            fontSize: '28px',
            color: '#e0f2fe',
            stroke: '#020617',
            strokeThickness: 5
        }).setOrigin(0.5);
    }

    private createCar(x: number, y: number, bodyColor: number, glassColor: number, player: boolean): GameObjects.Container {
        const root = this.add.container(x, y);
        const shadow = this.add.ellipse(0, 48, 64, 18, 0x020617, 0.42);
        const body = this.add.rectangle(0, 0, 62, 106, bodyColor).setStrokeStyle(4, 0x020617);
        const hood = this.add.rectangle(0, -31, 48, 28, bodyColor === 0x2dd4bf ? 0x67e8f9 : bodyColor, 0.92);
        const windshield = this.add.rectangle(0, -6, 38, 30, glassColor).setStrokeStyle(2, 0xbae6fd);
        const rearWindow = this.add.rectangle(0, 28, 34, 24, glassColor, 0.86);
        const leftWheelA = this.add.rectangle(-36, -28, 10, 28, 0x020617);
        const rightWheelA = this.add.rectangle(36, -28, 10, 28, 0x020617);
        const leftWheelB = this.add.rectangle(-36, 30, 10, 28, 0x020617);
        const rightWheelB = this.add.rectangle(36, 30, 10, 28, 0x020617);
        const leftLight = this.add.rectangle(-16, player ? -56 : 56, 12, 7, player ? 0xfef3c7 : 0xfca5a5);
        const rightLight = this.add.rectangle(16, player ? -56 : 56, 12, 7, player ? 0xfef3c7 : 0xfca5a5);
        root.add([shadow, leftWheelA, rightWheelA, leftWheelB, rightWheelB, body, hood, windshield, rearWindow, leftLight, rightLight]);
        return root;
    }

    private switchLane(direction: number): void {
        if (this.gameOver) {
            return;
        }
        this.playerLane = PhaserMath.Clamp(this.playerLane + direction, 0, this.laneXs.length - 1);
        this.tweens.add({
            targets: this.player,
            x: this.laneXs[this.playerLane],
            angle: direction * 5,
            duration: 120,
            yoyo: true,
            ease: 'Quad.easeOut'
        });
    }

    private spawnTraffic(): void {
        const lane = PhaserMath.Between(0, this.laneXs.length - 1);
        const color = PhaserMath.RND.pick([0xef4444, 0xf97316, 0xa855f7, 0x22c55e, 0xf59e0b]);
        const root = this.createCar(this.laneXs[lane], -90, color, 0x172554, false);
        root.angle = 180;
        this.traffic.push({ root, lane, speed: PhaserMath.Between(280, 390) });
    }

    private scrollLaneMarkers(delta: number): void {
        for (const marker of this.laneMarkers) {
            marker.y += delta * 0.34;
            if (marker.y > 830) {
                marker.y = -60;
            }
        }
    }

    private triggerGameOver(): void {
        this.gameOver = true;
        this.cameras.main.shake(180, 0.012);
        this.gameOverLayer = this.add.container(512, 384);
        this.gameOverLayer.add(this.add.rectangle(0, 0, 420, 220, 0x020617, 0.84).setStrokeStyle(2, 0x38bdf8));
        this.gameOverLayer.add(this.add.text(0, -48, 'COLLISION', {
            fontFamily: 'Trebuchet MS',
            fontSize: '48px',
            color: '#fecaca'
        }).setOrigin(0.5));
        const restart = this.add.text(0, 44, 'Press R or click to restart', {
            fontFamily: 'Trebuchet MS',
            fontSize: '22px',
            color: '#facc15'
        }).setOrigin(0.5).setInteractive({ useHandCursor: true });
        restart.on('pointerdown', () => this.reset());
        this.gameOverLayer.add(restart);
        this.refreshHud();
    }

    private reset(): void {
        this.distance = 0;
        this.spawnTimer = 0;
        this.gameOver = false;
        this.playerLane = 1;
        this.player.setPosition(this.laneXs[this.playerLane], 660);
        this.player.setAngle(0);
        for (const item of this.traffic) {
            item.root.destroy();
        }
        this.traffic = [];
        this.gameOverLayer?.destroy();
        this.gameOverLayer = undefined;
        this.refreshHud();
    }

    private refreshHud(): void {
        this.scoreText.setText(`Distance ${Math.floor(this.distance)}m`);
        this.statusText.setText(this.gameOver ? 'Crash detected - restart ready' : 'A/D or arrows to switch lanes');
    }

    private installTestBridge(): void {
        window.__GAME_TEST__ = {
            errors: this.errors,
            getState: () => ({
                score: Math.floor(this.distance),
                distance: Math.floor(this.distance),
                lane: this.playerLane,
                playerLane: this.playerLane,
                gameOver: this.gameOver,
                trafficCount: this.traffic.length,
                enemyCount: this.traffic.length
            }),
            reset: () => this.reset(),
            getErrors: () => this.errors
        };
    }
}
""",
        encoding="utf-8",
    )
