export class ScoreSystem {
    private value = 0;

    public get score(): number {
        return this.value;
    }

    public set(value: number): void {
        this.value = Math.max(0, Math.floor(value));
    }

    public add(points: number): number {
        this.set(this.value + points);
        return this.value;
    }

    public reset(): void {
        this.value = 0;
    }
}
