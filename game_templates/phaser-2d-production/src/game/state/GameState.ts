export type EntityState = {
    id: string;
    type: string;
    x: number;
    y: number;
    active: boolean;
};

export type RuntimeState = {
    running: boolean;
    paused: boolean;
    score: number;
    lives: number;
    level: number;
    objectiveProgress: number;
    objectiveTarget: number;
    player: { x: number; y: number };
    enemies: EntityState[];
    gameOver: boolean;
    winner: string | null;
};

export const createInitialState = (): RuntimeState => ({
    running: true,
    paused: false,
    score: 0,
    lives: 3,
    level: 1,
    objectiveProgress: 0,
    objectiveTarget: 10,
    player: { x: 512, y: 384 },
    enemies: [],
    gameOver: false,
    winner: null
});
