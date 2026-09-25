// Load test for the HPA demo. Offered load rises, holds, then falls, so you can
// see the gap between "load arrived" and "capacity arrived".
//
//   k6 run --out csv=load/k6-results.csv load/k6-script.js
//   (BASE_URL defaults to the k3d ingress on port 8081)
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8081";

export const options = {
  stages: [
    { duration: "30s", target: 5 },  // warm-up
    { duration: "1m", target: 40 },  // offered load rises
    { duration: "3m", target: 40 },  // hold: watch replicas climb
    { duration: "1m", target: 0 },   // load falls (scale-down waits 300 s)
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  // Reading a full page of 100 complaints is CPU work for the backend
  // (query + serialisation), which is what the HPA measures.
  const res = http.get(`${BASE}/api/complaints?page_size=100`);
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(0.1);
}
