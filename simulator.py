"""
Event simulator for Cyber-Visceral Link.
Simulates Witcher 3 game events by writing to RAM disk log.
"""
import asyncio
import random
import argparse
from datetime import datetime
from pathlib import Path

# Event types to simulate
EVENT_TYPES = [
    "GORE_EVENT",
    "DAMAGE_EVENT",
    "KILL_EVENT",
    "COMBO_EVENT",
    "CRITICAL_EVENT",
    "ADRENALINE_EVENT",
    "LOW_HEALTH_EVENT",
    "DEATH_EVENT"
]


class EventSimulator:
    """Simulates game events for testing."""
    
    def __init__(self, log_path: str = "/dev/shm/witcher_events.log"):
        self.log_path = Path(log_path)
        self.is_running = False
    
    def write_event(self, event: str) -> None:
        """Write a single event to the log file."""
        try:
            with open(self.log_path, 'a') as f:
                timestamp = datetime.now().isoformat()
                f.write(f"{timestamp} - {event}\n")
            print(f"[SIMULATOR] Wrote: {event}")
        except Exception as e:
            print(f"[SIMULATOR] Error writing event: {e}")
    
    async def simulate_random(self, interval: float = 1.0) -> None:
        """Simulate random events at specified interval."""
        self.is_running = True
        print(f"[SIMULATOR] Starting random event simulation (interval: {interval}s)")
        print(f"[SIMULATOR] Writing to: {self.log_path}")
        
        try:
            while self.is_running:
                event = random.choice(EVENT_TYPES)
                self.write_event(event)
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print("\n[SIMULATOR] Stopped by user")
        finally:
            self.is_running = False
    
    async def simulate_combat_sequence(self) -> None:
        """Simulate a combat sequence with realistic timing."""
        self.is_running = True
        print(f"[SIMULATOR] Starting combat sequence simulation")
        print(f"[SIMULATOR] Writing to: {self.log_path}")
        
        try:
            while self.is_running:
                # Combat start
                self.write_event("ADRENALINE_EVENT")
                await asyncio.sleep(2)
                
                # Exchange hits
                for _ in range(random.randint(3, 8)):
                    self.write_event("DAMAGE_EVENT")
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                    
                    if random.random() > 0.7:
                        self.write_event("CRITICAL_EVENT")
                        await asyncio.sleep(0.3)
                
                # Combo
                self.write_event("COMBO_EVENT")
                await asyncio.sleep(1)
                
                # Gore finish
                if random.random() > 0.5:
                    self.write_event("GORE_EVENT")
                    await asyncio.sleep(0.5)
                
                # Kill
                self.write_event("KILL_EVENT")
                await asyncio.sleep(random.uniform(2, 5))
                
        except KeyboardInterrupt:
            print("\n[SIMULATOR] Stopped by user")
        finally:
            self.is_running = False
    
    async def simulate_stress_test(self, events_per_second: int = 10) -> None:
        """Stress test with high event rate."""
        self.is_running = True
        interval = 1.0 / events_per_second
        print(f"[SIMULATOR] Starting stress test ({events_per_second} events/sec)")
        print(f"[SIMULATOR] Writing to: {self.log_path}")
        
        try:
            count = 0
            while self.is_running:
                event = random.choice(EVENT_TYPES)
                self.write_event(event)
                count += 1
                if count % 100 == 0:
                    print(f"[SIMULATOR] Sent {count} events")
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n[SIMULATOR] Stopped after {count} events")
        finally:
            self.is_running = False
    
    def stop(self) -> None:
        """Stop the simulator."""
        self.is_running = False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Cyber-Visceral Link Event Simulator")
    parser.add_argument(
        "--mode",
        choices=["random", "combat", "stress"],
        default="random",
        help="Simulation mode"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Event interval in seconds (for random mode)"
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=10,
        help="Events per second (for stress mode)"
    )
    parser.add_argument(
        "--log-path",
        type=str,
        default="/dev/shm/witcher_events.log",
        help="Path to log file"
    )
    
    args = parser.parse_args()
    
    simulator = EventSimulator(args.log_path)
    
    if args.mode == "random":
        await simulator.simulate_random(args.interval)
    elif args.mode == "combat":
        await simulator.simulate_combat_sequence()
    elif args.mode == "stress":
        await simulator.simulate_stress_test(args.rate)


if __name__ == "__main__":
    asyncio.run(main())
