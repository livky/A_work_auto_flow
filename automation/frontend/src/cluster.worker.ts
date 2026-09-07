import { cluster } from "./cluster";
self.onmessage = (event) => {
  try {
    self.postMessage({
      result: cluster(event.data.graph, event.data.semantic),
    });
  } catch (error) {
    self.postMessage({ error: String(error) });
  }
};
