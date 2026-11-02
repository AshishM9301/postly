export type Coordinates = {
  lat: number;
  lng: number;
};

/**
 * Browser GPS. `localhost` counts as a secure context, so this works in dev.
 * Rejections carry a message the caller can show; PIN/name search still works.
 */
export function getBrowserLocation(): Promise<Coordinates> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      reject(new Error("This browser does not support location."));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        }),
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          reject(
            new Error(
              "Location permission denied. Type a PIN or search your area instead.",
            ),
          );
        } else {
          reject(new Error("Could not get your location. Try a PIN or name search."));
        }
      },
      { enableHighAccuracy: false, timeout: 8000, maximumAge: 60_000 },
    );
  });
}
