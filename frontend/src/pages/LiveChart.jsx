import { useEffect, useRef, useState } from 'react'
import { CrosshairMode, LineStyle, createChart } from 'lightweight-charts'
import { fetchCandles, fetchChartTrades } from '../services/api'

const timeframes = ['M1', 'M5', 'M15', 'H1', 'H4', 'D1']

function toChartCandle(candle) {
  return {
    time: Math.floor(new Date(candle.time).getTime() / 1000),
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close),
  }
}

function toLinePoint(candle, key) {
  if (candle[key] == null || candle[key] === '') return null
  const value = Number(candle[key])
  return Number.isFinite(value)
    ? { time: Math.floor(new Date(candle.time).getTime() / 1000), value }
    : null
}

function formatChartTime(time) {
  if (typeof time === 'number') return new Date(time * 1000).toLocaleString()
  if (time && typeof time === 'object') {
    return new Date(Date.UTC(time.year, time.month - 1, time.day)).toLocaleDateString()
  }
  return '—'
}

export default function LiveChart({ lastEvent }) {
  const chartContainer = useRef(null)
  const chartRef = useRef(null)
  const seriesRef = useRef(null)
  const lineRefs = useRef({})
  const priceLinesRef = useRef([])
  const visibleRangeInitializedRef = useRef(false)
  const chartDataInitializedRef = useRef(false)
  const chartCandleCountRef = useRef(0)
  const [timeframe, setTimeframe] = useState('M15')
  const [candles, setCandles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [signal, setSignal] = useState(null)
  const [selectedCandle, setSelectedCandle] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [chartTrades, setChartTrades] = useState([])
  const [lastCandleUpdate, setLastCandleUpdate] = useState(null)

  useEffect(() => {
    if (lastEvent?.type === 'agent_update') setSignal(lastEvent.payload?.signal || null)
  }, [lastEvent])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    setCandles([])
    setLastCandleUpdate(null)
    setSelectedCandle(null)
    visibleRangeInitializedRef.current = false
    chartDataInitializedRef.current = false
    chartCandleCountRef.current = 0
    fetchCandles(timeframe)
      .then((data) => {
        if (!cancelled) {
          setCandles(data.candles || [])
          setLastCandleUpdate(data.candles?.at(-1)?.time || null)
        }
      })
      .catch((requestError) => {
        if (!cancelled) {
          setCandles([])
          setError(requestError.message)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    fetchChartTrades()
      .then((data) => {
        if (!cancelled) setChartTrades(data.trades || [])
      })
      .catch(() => {
        if (!cancelled) setChartTrades([])
      })
    return () => {
      cancelled = true
    }
  }, [timeframe, refreshKey])

  useEffect(() => {
    if (!chartContainer.current) return undefined
    const chart = createChart(chartContainer.current, {
      layout: { background: { color: '#ffffff' }, textColor: '#737373' },
      grid: { vertLines: { color: '#f0f0f0' }, horzLines: { color: '#f0f0f0' } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#dedede' },
      timeScale: { borderColor: '#dedede', timeVisible: true },
      width: chartContainer.current.clientWidth,
      height: 520,
    })
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })
    const colors = { ema_20: '#f59e0b', ema_50: '#38bdf8', ema_200: '#c084fc' }
    const lines = {}
    Object.entries(colors).forEach(([key, color]) => {
      lines[key] = chart.addLineSeries({
        color,
        lineWidth: key === 'ema_200' ? 2 : 1,
        lineStyle: LineStyle.Solid,
        title: key.replace('ema_', 'EMA '),
      })
    })
    chartRef.current = chart
    seriesRef.current = candleSeries
    lineRefs.current = lines
    candleSeries.priceScale().applyOptions({
      autoScale: true,
      scaleMargins: { top: 0.1, bottom: 0.1 },
    })
    const handleCrosshairMove = (param) => {
      if (!param.time || !param.seriesData) {
        setSelectedCandle(null)
        return
      }
      const candle = param.seriesData.get(candleSeries)
      if (candle) setSelectedCandle({ ...candle, time: param.time })
    }
    chart.subscribeCrosshairMove(handleCrosshairMove)
    const observer = new ResizeObserver(() => {
      if (chartContainer.current) {
        chart.applyOptions({ width: chartContainer.current.clientWidth })
      }
    })
    observer.observe(chartContainer.current)
    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
      observer.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!seriesRef.current) return
    if (!candles.length) {
      seriesRef.current.setData([])
      seriesRef.current.setMarkers([])
      Object.values(lineRefs.current).forEach((line) => line.setData([]))
      priceLinesRef.current.forEach((line) => seriesRef.current.removePriceLine(line))
      priceLinesRef.current = []
      return
    }
    const chartCandles = candles.map(toChartCandle).filter((candle) =>
      Number.isFinite(candle.open)
      && Number.isFinite(candle.high)
      && Number.isFinite(candle.low)
      && Number.isFinite(candle.close)
      && candle.high >= candle.low
    )
    if (!chartCandles.length) return
    const shouldReplaceData = !chartDataInitializedRef.current
      || chartCandleCountRef.current !== chartCandles.length
    if (shouldReplaceData) {
      seriesRef.current.setData(chartCandles)
      chartDataInitializedRef.current = true
      chartCandleCountRef.current = chartCandles.length
    } else {
      seriesRef.current.update(chartCandles[chartCandles.length - 1])
    }
    seriesRef.current.setMarkers(chartTrades
      .filter((trade) => trade.time >= chartCandles[0].time && trade.time <= chartCandles[chartCandles.length - 1].time)
      .map((trade) => ({
        time: trade.time,
        position: trade.side === 'buy' ? 'belowBar' : 'aboveBar',
        color: trade.kind === 'exit' ? '#111111' : trade.side === 'buy' ? '#159447' : '#d93030',
        shape: trade.kind === 'exit' ? 'circle' : trade.side === 'buy' ? 'arrowUp' : 'arrowDown',
        text: trade.kind === 'exit' ? `EXIT ${Number(trade.profit || 0).toFixed(2)}` : `ENTRY ${trade.side.toUpperCase()}`,
      })))
    Object.keys(lineRefs.current).forEach((key) => {
      if (shouldReplaceData) {
        lineRefs.current[key].setData(
          candles.map((candle) => toLinePoint(candle, key)).filter(Boolean),
        )
      } else {
        const latestPoint = toLinePoint(candles[candles.length - 1], key)
        if (latestPoint) lineRefs.current[key].update(latestPoint)
      }
    })
    const timeScale = chartRef.current?.timeScale()
    if (!visibleRangeInitializedRef.current) {
      timeScale?.setVisibleLogicalRange({
        from: Math.max(0, chartCandles.length - 120),
        to: chartCandles.length + 5,
      })
      visibleRangeInitializedRef.current = true
    }
    seriesRef.current.priceScale().applyOptions({ autoScale: true })
    setSelectedCandle((current) => current || {
      ...toChartCandle(candles[candles.length - 1]),
      time: Math.floor(new Date(candles[candles.length - 1].time).getTime() / 1000),
    })
  }, [candles, chartTrades])

  useEffect(() => {
    if (!seriesRef.current) return
    priceLinesRef.current.forEach((line) => seriesRef.current.removePriceLine(line))
    priceLinesRef.current = []
    if (!signal || timeframe !== 'M15' || !candles.length) return
    const levels = [
      ['entry', '#f8fafc', 'Entry'],
      ['sl', '#ef4444', 'Stop loss'],
      ['tp', '#22c55e', 'Take profit'],
    ]
    const values = levels.map(([key]) => Number(signal[key]))
    const prices = candles.flatMap((candle) => [Number(candle.low), Number(candle.high)])
      .filter((value) => Number.isFinite(value))
    const minimum = Math.min(...prices)
    const maximum = Math.max(...prices)
    const padding = Math.max((maximum - minimum) * 0.1, 1)
    const validSignal = values.every((value) => Number.isFinite(value))
      && values.every((value) => value >= minimum - padding && value <= maximum + padding)
    if (!validSignal) return
    priceLinesRef.current = levels.map(([key, color, title]) =>
      seriesRef.current.createPriceLine({
        price: Number(signal[key]),
        color,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title,
      }),
    )
  }, [signal, candles, timeframe])

  useEffect(() => {
    if (lastEvent?.type !== 'candle_update' || lastEvent.payload?.timeframe !== timeframe) return
    const candle = lastEvent.payload.candle
    setCandles((current) => {
      const next = current.filter((item) => item.time !== candle.time)
      return [...next, candle].sort((a, b) => new Date(a.time) - new Date(b.time)).slice(-300)
    })
    setLastCandleUpdate(candle.time)
  }, [lastEvent, timeframe])

  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">MARKET DATA / XAUUSD</p>
          <h1>Live Gold Chart</h1>
        </div>
        <div className="chart-actions">
          <button
            className="refresh-button"
            disabled={loading}
            onClick={() => setRefreshKey((current) => current + 1)}
            type="button"
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
          <div className="timeframes">
          {timeframes.map((value) => (
            <button
              className={value === timeframe ? 'active' : ''}
              key={value}
              onClick={() => setTimeframe(value)}
              type="button"
            >
              {value}
            </button>
          ))}
          </div>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="chart-card">
        <div className="chart-meta">
          <span>XAUUSD · {timeframe}</span>
          <span className={lastCandleUpdate ? 'chart-live-status' : ''}>
            {loading ? 'Loading candles…' : `${candles.length} candles · ${lastCandleUpdate ? `last ${new Date(lastCandleUpdate).toLocaleTimeString()}` : 'no live update'}`}
          </span>
        </div>
        <div className="ohlc-readout">
          {selectedCandle ? (
            <>
              <span className="candle-time">{formatChartTime(selectedCandle.time)}</span>
              <span>O <b>{selectedCandle.open}</b></span>
              <span>H <b>{selectedCandle.high}</b></span>
              <span>L <b>{selectedCandle.low}</b></span>
              <span>C <b className={selectedCandle.close >= selectedCandle.open ? 'positive' : 'negative'}>{selectedCandle.close}</b></span>
            </>
          ) : <span>Move your cursor over a candle to inspect OHLC data</span>}
        </div>
        <div className="chart" ref={chartContainer} />
      </div>
      <div className="legend">
        <span className="ema20">EMA 20</span>
        <span className="ema50">EMA 50</span>
        <span className="ema200">EMA 200</span>
        {signal && <span>Signal: {signal.side.toUpperCase()} · Entry {signal.entry} · SL {signal.sl} · TP {signal.tp}</span>}
      </div>
    </section>
  )
}