// Zero-downtime check: run this, and DURING it run `kubectl set image ...`.
// The test fails if even one request fails.
//
//   k6 run load/rollout-check.js
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8081";

export const options = {
  vus: 10,
  duration: "2m",
  thresholds: {
    http_req_failed: ["rate==0"], // zero failed requests, not "few"
  },
};

export default function () {
  const res = http.get(`${BASE}/api/stats`);
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(0.2);
}
