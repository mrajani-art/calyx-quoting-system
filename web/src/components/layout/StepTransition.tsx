"use client";

import { useRef, useEffect, useState } from "react";

interface Props {
  stepKey: string;
  children: React.ReactNode;
}

export default function StepTransition({ stepKey, children }: Props) {
  const [visible, setVisible] = useState(false);
  const prevKey = useRef(stepKey);

  useEffect(() => {
    if (stepKey !== prevKey.current) {
      setVisible(false);
      const timer = setTimeout(() => {
        prevKey.current = stepKey;
        setVisible(true);
      }, 50);
      return () => clearTimeout(timer);
    } else {
      setVisible(true);
    }
  }, [stepKey]);

  return (
    <div
      className={`transition-all duration-300 ease-out ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2"
      }`}
    >
      {children}
    </div>
  );
}
