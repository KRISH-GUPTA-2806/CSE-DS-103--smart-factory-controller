import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const equipmentNames = ['lights', 'fan', 'exhaust', 'machinery']

export default function App() {
  const [lastCommand, setLastCommand] = useState(null)
  const [auth, setAuth] = useState(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [rows, setRows] = useState([])
  const [analytics, setAnalytics] = useState({
    forecast: [],
    anomalies: [],
  })
  const [schedules, setSchedules] = useState([])
  const [notice, setNotice] = useState('')
  const [scheduleForm, setScheduleForm] = useState({
    equipment: 'lights',
    action: 'on',
    run_at: '',
  })

  const request = useCallback(
    async (path, options = {}) => {
      const response = await fetch(path, {
        ...options,
        headers: {
          Authorization: `Basic ${btoa(
            `${auth.username}:${auth.password}`,
          )}`,
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Request failed')
      }

      return data
    },
    [auth],
  )

  const refresh = useCallback(async () => {
    if (!auth) return

    try {
      const [telemetry, model, agenda] = await Promise.all([
        request('/api/telemetry?limit=100'),
        request('/api/analytics'),
        request('/api/schedules'),
      ])

      setRows(telemetry.reverse())
      setAnalytics(model)
      setSchedules(agenda)
    } catch (error) {
      setNotice(error.message)
    }
  }, [auth, request])

  useEffect(() => {
    if (!auth) return

    refresh()
    const timer = setInterval(refresh, 3000)

    return () => clearInterval(timer)
  }, [auth, refresh])

  async function login(event) {
    event.preventDefault()

    try {
      const response = await fetch('/api/telemetry?limit=1', {
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
        },
      })

      if (!response.ok) {
        throw new Error(
          'Login failed. Check credentials in the project .env file.',
        )
      }

      setAuth({ username, password })
      setLoginError('')
    } catch (error) {
      setLoginError(error.message)
    }
  }

  async function sendCommand(equipment, action) {
  try {
    await request('/api/commands', {
      method: 'POST',
      body: JSON.stringify({ equipment, action }),
    })

    setLastCommand({ equipment, action })
    setNotice(`${equipment} ${action} command sent to simulator`)
  } catch (error) {
    setNotice(error.message)
  }
}

  async function runOptimizer() {
    try {
      const result = await request('/api/optimize?apply=true', {
        method: 'POST',
      })

      if (result.recommendations.length) {
        setNotice(
          `Optimizer sent ${result.recommendations.length} command(s): ` +
            result.recommendations
              .map((item) => `${item.equipment} — ${item.reason}`)
              .join('; '),
        )
      } else {
        setNotice(
          'No energy-saving command recommended for the current conditions.',
        )
      }

      refresh()
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function createSchedule(event) {
    event.preventDefault()

    try {
      await request('/api/schedules', {
        method: 'POST',
        body: JSON.stringify({
          ...scheduleForm,
          run_at: new Date(scheduleForm.run_at).toISOString(),
        }),
      })

      setScheduleForm({
        ...scheduleForm,
        run_at: '',
      })
      setNotice(
        'Schedule saved. It runs while the API and HiveMQ connection are active.',
      )
      refresh()
    } catch (error) {
      setNotice(error.message)
    }
  }

  async function removeSchedule(id) {
    try {
      await request(`/api/schedules/${id}`, {
        method: 'DELETE',
      })
      refresh()
    } catch (error) {
      setNotice(error.message)
    }
  }

  const latest = rows.at(-1)

  const average = useMemo(() => {
    if (!rows.length) return 0

    return (
      rows.reduce(
        (sum, row) => sum + Number(row.usage_kwh),
        0,
      ) / rows.length
    )
  }, [rows])

  const occupancyRate = rows.length
    ? (100 *
        rows.filter((row) => Number(row.people_count) > 0).length) /
      rows.length
    : 0

  const chartData = rows.map((row) => ({
    ...row,
    time: new Date(row.source_timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    }),
  }))

  const forecastData =
    analytics.forecast?.map((point) => ({
      ...point,
      time: new Date(point.timestamp).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
      }),
    })) || []

  if (!auth) {
    return (
      <main className="login-wrap">
        <form className="login-card" onSubmit={login}>
          <div className="eyebrow">PLC-LITE · SOFTWARE DEMO</div>
          <h1>Factory monitor</h1>
          <p>
            Sign in with the dashboard credentials configured in your .env file.
          </p>

          <label>
            Username
            <input
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
            />
          </label>

          {loginError && <div className="error">{loginError}</div>}

          <button className="primary full">Sign in</button>
        </form>
      </main>
    )
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">PLC-LITE · SOFTWARE CONTROL ROOM</div>
          <h1>Factory monitor</h1>
        </div>

        <div className="header-actions">
          <div className="live">
            <span />
            Dataset replay
          </div>
          <button className="ghost" onClick={() => setAuth(null)}>
            Sign out
          </button>
        </div>
      </header>

      <section className="notice">
        <b>Software simulation:</b> steel energy, room occupancy, and machine
        maintenance readings are public historical datasets from different
        sources. Equipment responds to commands in the simulator; controls do
        not operate physical equipment.
      </section>

      {notice && (
        <section className="notice result">
          {notice}
          <button
            className="close"
            onClick={() => setNotice('')}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </section>
      )}

      <section className="cards">
        <Metric
          title="Latest energy"
          value={
            latest
              ? `${Number(latest.usage_kwh).toFixed(2)} kWh`
              : '—'
          }
          detail="UCI steel industry · historical"
        />

        <Metric
          title="Average in view"
          value={
            rows.length
              ? `${average.toFixed(2)} kWh`
              : '—'
          }
          detail={`${rows.length} replay readings`}
        />

        <Metric
          title="People in room"
          value={latest?.people_count ?? '—'}
          detail="UCI count · separate test room"
        />

        <Metric
          title="Occupied time"
          value={
            rows.length
              ? `${occupancyRate.toFixed(0)}%`
              : '—'
          }
          detail="Recent window · productivity proxy"
        />

        <Metric
          title="Machine failure risk"
          value={
            latest?.maintenance_risk != null
              ? `${(Number(latest.maintenance_risk) * 100).toFixed(1)}%`
              : '—'
          }
          detail="AI4I model · synthetic maintenance data"
        />
      </section>

      <section className="grid-two">
        <section className="panel">
          <PanelTitle
            kicker="ENERGY HISTORY"
            title="Usage replay"
            badge={latest?.load_type || 'Dataset'}
          />

          <div className="chart">
            {chartData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid
                    stroke="#26333b"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="time"
                    minTickGap={32}
                    tick={{ fill: '#8d9da5', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#8d9da5', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#17232a',
                      border: '1px solid #34434c',
                      borderRadius: 8,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="usage_kwh"
                    name="Usage (kWh)"
                    stroke="#6de0b2"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">
                Start the simulator to stream readings.
              </div>
            )}
          </div>
        </section>

        <section className="panel">
          <PanelTitle
            kicker="PREDICTIVE ANALYTICS"
            title="Energy forecast"
            badge="Random Forest"
          />

          <p className="subtle">
            {analytics.model || 'Waiting for readings'}
          </p>

          <div className="chart">
            {forecastData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={forecastData}>
                  <CartesianGrid
                    stroke="#26333b"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="time"
                    minTickGap={30}
                    tick={{ fill: '#8d9da5', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fill: '#8d9da5', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#17232a',
                      border: '1px solid #34434c',
                      borderRadius: 8,
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="usage_kwh"
                    name="Forecast (kWh)"
                    stroke="#9d8cff"
                    dot={false}
                    strokeWidth={2}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="chart-empty">
                Forecast appears after 20 readings.
              </div>
            )}
          </div>
        </section>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <PanelTitle
            kicker="SIMULATED PLC OUTPUTS"
            title="Equipment control"
            badge={latest?.control_mode || 'Waiting'}
          />
          <button className="primary" onClick={runOptimizer}>
            Run load optimizer
          </button>
        </div>

        <div className="equipment">
          {equipmentNames.map((name) => {
            const state = latest?.equipment?.[name] ?? '—'
            const runtime =
              latest?.equipment_runtime_hours?.[name]

            return (
              <article className="equipment-item" key={name}>
                <span
                  className={`state ${state === 'on' ? 'on' : ''}`}
                />

                <div className="equip-label">
                  <span>{name}</span>
                  <strong>{state}</strong>
                </div>

                <div className="runtime">
                  Replay operating time:{' '}
                  {runtime != null
                    ? `${Number(runtime).toFixed(2)} h`
                    : '—'}
                </div>

                <div className="control-actions">
                  <button
                    className={`tiny ${lastCommand?.equipment === name && lastCommand?.action === 'on' ? 'selected' : ''}`}
                    onClick={() => sendCommand(name, 'on')}
                  >
                    On
                  </button>
                  <button
                    className={`tiny ${lastCommand?.equipment === name && lastCommand?.action === 'off' ? 'selected' : ''}`}
                    onClick={() => sendCommand(name, 'off')}
                  >
                    Off
                  </button>
                  <button
                    className={`tiny auto ${lastCommand?.equipment === name && lastCommand?.action === 'auto' ? 'selected' : ''}`}
                    onClick={() => sendCommand(name, 'auto')}
                  >
                    Auto
                  </button>
                </div>
              </article>
            )
          })}
        </div>

        <p className="subtle">
          The optimizer can switch lights off when the recorded room is empty,
          or switch the fan off when demand is high and occupancy is low.
          Exhaust and machinery are protected from automatic shutoff.
        </p>
      </section>

      <section className="grid-two">
        <section className="panel">
          <PanelTitle
            kicker="AUTOMATION"
            title="Schedules"
            badge="Runs in API"
          />

          <form className="schedule-form" onSubmit={createSchedule}>
            <select
              value={scheduleForm.equipment}
              onChange={(event) =>
                setScheduleForm({
                  ...scheduleForm,
                  equipment: event.target.value,
                })
              }
            >
              {equipmentNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>

            <select
              value={scheduleForm.action}
              onChange={(event) =>
                setScheduleForm({
                  ...scheduleForm,
                  action: event.target.value,
                })
              }
            >
              <option value="on">Turn on</option>
              <option value="off">Turn off</option>
            </select>

            <input
              required
              type="datetime-local"
              value={scheduleForm.run_at}
              onChange={(event) =>
                setScheduleForm({
                  ...scheduleForm,
                  run_at: event.target.value,
                })
              }
            />

            <button className="primary">Add</button>
          </form>

          <div className="list">
            {schedules
              .filter((item) => item.enabled)
              .map((item) => (
                <div className="list-row" key={item.id}>
                  <span>
                    <b>{item.equipment}</b> {item.action} ·{' '}
                    {new Date(item.run_at).toLocaleString()}
                  </span>
                  <button
                    className="ghost"
                    onClick={() => removeSchedule(item.id)}
                  >
                    Cancel
                  </button>
                </div>
              ))}

            {!schedules.some((item) => item.enabled) && (
              <p className="subtle">No upcoming schedules.</p>
            )}
          </div>
        </section>

        <section className="panel">
          <PanelTitle
            kicker="PROACTIVE MAINTENANCE"
            title="Energy anomaly alerts"
            badge={`${analytics.anomalies?.length || 0} detected`}
          />

          {latest?.maintenance_risk >= 0.35 && (
            <div className="risk-alert">
              <b>Machine maintenance alert</b>
              <span>
                Model risk{' '}
                {(Number(latest.maintenance_risk) * 100).toFixed(1)}%
                {' · '}review simulated machine sample{' '}
                {latest.maintenance_source_record}
              </span>
            </div>
          )}

          <div className="list">
            {analytics.anomalies
              ?.slice()
              .reverse()
              .map((item, index) => (
                <div
                  className="list-row"
                  key={`${item.timestamp}-${index}`}
                >
                  <span>
                    <b>{Number(item.usage_kwh).toFixed(2)} kWh</b>
                    {' · '}robust deviation score {item.score}
                  </span>
                  <time>
                    {new Date(item.timestamp).toLocaleString()}
                  </time>
                </div>
              ))}

            {!analytics.anomalies?.length &&
              latest?.maintenance_risk < 0.35 && (
                <p className="subtle">
                  No energy or maintenance alerts in the current window.
                </p>
              )}
          </div>
        </section>
      </section>

      <section className="panel">
        <PanelTitle
          kicker="MACHINE HEALTH MODEL"
          title="Predictive maintenance signals"
          badge="AI4I holdout predictions"
        />

        <p className="subtle">
          The risk score comes from a Random Forest trained on the UCI AI4I
          synthetic predictive-maintenance dataset. These machine readings
          are a separate sample, not readings from the steel-energy site.
        </p>

        <div className="sensor-strip">
          <Metric
            title="Predicted failure risk"
            value={
              latest?.maintenance_risk != null
                ? `${(Number(latest.maintenance_risk) * 100).toFixed(1)}%`
                : '—'
            }
            detail="Model probability"
          />

          <Metric
            title="Recorded test outcome"
            value={
              latest?.machine_failure == null
                ? '—'
                : Number(latest.machine_failure)
                  ? 'Failure'
                  : 'No failure'
            }
            detail="AI4I holdout label"
          />

          {Object.entries(latest?.maintenance_sensors || {}).map(
            ([key, value]) => (
              <Metric
                key={key}
                title={key.replace(/ \[[^\]]+\]/g, '')}
                value={Number(value).toFixed(1)}
                detail={key.match(/\[([^\]]+)\]/)?.[1] || 'Sensor'}
              />
            ),
          )}
        </div>
      </section>

      <section className="panel">
        <PanelTitle
          kicker="OCCUPANCY SENSOR DATA"
          title="Room environment"
          badge="UCI test room"
        />

        <div className="sensor-strip">
          <Metric
            title="Temperature"
            value={
              latest?.room_temperature != null
                ? `${Number(latest.room_temperature).toFixed(1)} °C`
                : '—'
            }
            detail="Recorded sensor data"
          />

          <Metric
            title="Humidity"
            value={
              latest?.room_humidity != null
                ? `${Number(latest.room_humidity).toFixed(1)} %`
                : '—'
            }
            detail="Recorded sensor data"
          />

          <Metric
            title="Light"
            value={
              latest?.room_light != null
                ? `${Number(latest.room_light).toFixed(0)} lux`
                : '—'
            }
            detail="Recorded sensor data"
          />

          <Metric
            title="CO₂"
            value={
              latest?.room_co2 != null
                ? `${Number(latest.room_co2).toFixed(0)} ppm`
                : '—'
            }
            detail="Recorded sensor data"
          />

          <Metric
            title="PIR motion"
            value={
              latest?.room_pir != null
                ? `${latest.room_pir} active`
                : '—'
            }
            detail="Recorded PIR sensors"
          />
        </div>
      </section>

      <footer>
        Dataset readings are historical. Commands, schedules, and PLC behavior
        run in a software simulation. MQTT uses TLS and AES-GCM message
        protection.
      </footer>
    </main>
  )
}

function Metric({ title, value, detail }) {
  return (
    <article className="metric">
      <div className="eyebrow">{title}</div>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  )
}

function PanelTitle({ kicker, title, badge }) {
  return (
    <div className="panel-heading">
      <div>
        <div className="eyebrow">{kicker}</div>
        <h2>{title}</h2>
      </div>
      {badge && <span className="source-tag">{badge}</span>}
    </div>
  )
}