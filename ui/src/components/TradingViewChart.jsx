import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts';

export default function TradingViewChart({ data = [], ticker = "STOCK" }) {
  const chartContainerRef = useRef();

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Standard AITradra V4 Theme Colors
    const colors = {
      backgroundColor: 'transparent',
      lineColor: '#00f0ff',
      textColor: '#94a3b8',
      areaTopColor: 'rgba(0, 240, 255, 0.15)',
      areaBottomColor: 'rgba(0, 240, 255, 0.01)',
      gridColor: 'rgba(255, 255, 255, 0.03)',
    };

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current.clientWidth });
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: colors.backgroundColor },
        textColor: colors.textColor,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: colors.gridColor },
        horzLines: { color: colors.gridColor },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      crosshair: {
        mode: 0, // Normal crosshair
        vertLine: {
          color: 'rgba(255,255,255,0.2)',
          width: 0.5,
          style: 2, // Dashed
          labelBackgroundColor: '#1e232b',
        },
        horzLine: {
          color: 'rgba(255,255,255,0.2)',
          width: 0.5,
          style: 2,
          labelBackgroundColor: '#1e232b',
        },
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.1)',
        timeVisible: true,
      },
    });

    // v5 API: Unified addSeries method
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#00f0ff',
      downColor: '#ff2a5f',
      borderVisible: false,
      wickUpColor: '#00f0ff',
      wickDownColor: '#ff2a5f',
    });

    // Formatting incoming data for Lightweight Charts
    // Data expected: [{ t: timestamp/date, o: open, h: high, l: low, c: close }, ...]
    const formattedData = data.map(d => ({
      time: typeof d.t === 'number' ? d.t / 1000 : (new Date(d.t).getTime() / 1000),
      open: Number(d.o),
      high: Number(d.h),
      low: Number(d.l),
      close: Number(d.c),
    })).sort((a,b) => a.time - b.time);

    // Deduplicate timestamps if they exist (sometimes multiple agents report same time)
    const uniqueData = [];
    const seenTimes = new Set();
    for(const d of formattedData) {
        if(!seenTimes.has(d.time)) {
            uniqueData.push(d);
            seenTimes.add(d.time);
        }
    }

    if (uniqueData.length > 0) {
      candlestickSeries.setData(uniqueData);
      chart.timeScale().fitContent();
    }

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, ticker]);

  return (
    <div className="relative w-full h-[400px]">
      <div ref={chartContainerRef} className="w-full h-full" />
      <div className="absolute top-4 left-4 pointer-events-none">
        <span className="text-[10px] font-black tracking-widest text-[#00f0ff] uppercase opacity-40">Axiom Data Stream // {ticker}</span>
      </div>
    </div>
  );
}
