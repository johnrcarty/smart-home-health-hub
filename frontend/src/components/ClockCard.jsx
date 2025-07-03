import { useState, useEffect } from "react";

export default function ClockCard() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const formatDate = (date) => {
    const options = { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    };
    return date.toLocaleDateString(undefined, options);
  };

  const formatTime = (date) => {
    const options = { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      hour12: true 
    };
    return date.toLocaleTimeString(undefined, options);
  };

  return (
    <div className="clock-card">
      <div className="clock-time">{formatTime(time)}</div>
      <div className="clock-date">{formatDate(time)}</div>
    </div>
  );
}
