# This file implements zone and runtime manual selection for irrigation.

class IrrigationController:
    def __init__(self, zones):
        self.zones = zones

    def select_zone(self, zone_id):
        if zone_id in self.zones:
            print(f"Zone {zone_id} selected.")
            return zone_id
        else:
            print("Invalid zone selected.")
            return None

    def start_irrigation(self, zone_id, runtime):
        if zone_id not in self.zones:
            print("Zone does not exist.")
            return

        print(f"Starting irrigation in Zone {zone_id} for {runtime} minutes.")
        # Logic to start irrigation in the specified zone
        # This will include hardware control logic

    def stop_irrigation(self, zone_id):
        if zone_id not in self.zones:
            print("Zone does not exist.")
            return

        print(f"Stopping irrigation in Zone {zone_id}.")
        # Logic to stop irrigation in the specified zone
        # This will include hardware control logic


def main():
    zones = [1, 2, 3, 4]  # Example zones
    controller = IrrigationController(zones)

    # Example Usage
    selected_zone = controller.select_zone(2)
    if selected_zone is not None:
        controller.start_irrigation(selected_zone, runtime=15)
        controller.stop_irrigation(selected_zone)


if __name__ == "__main__":
    main()