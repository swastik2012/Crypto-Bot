import React, { createContext, useContext, useState, useEffect, useMemo, type ReactNode } from 'react';
import { api } from '../services/api';

export type CurrencyCode = 'USD' | 'INR';

interface CurrencyContextType {
  currency: CurrencyCode;
  currencySymbol: string;
  exchangeRate: number; // 1 USD = exchangeRate INR
  liveInrRate: number;
  setCurrency: (code: CurrencyCode) => void;
  toggleCurrency: () => void;
  formatPrice: (amountInUSD: number, decimals?: number) => string;
  formatRawNumber: (amountInUSD: number, decimals?: number) => number;
}

const STORAGE_KEY = 'aethertrade_selected_currency_v1';
const DEFAULT_USD_TO_INR = 95.47; // Live market reference

const CurrencyContext = createContext<CurrencyContextType | undefined>(undefined);

export const CurrencyProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currency, setCurrencyState] = useState<CurrencyCode>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved === 'INR' || saved === 'USD' ? saved : 'USD';
    } catch {
      return 'USD';
    }
  });

  const [liveInrRate, setLiveInrRate] = useState<number>(DEFAULT_USD_TO_INR);

  // Poll real-time live USD/INR exchange rate from API & global Forex feed
  useEffect(() => {
    let isMounted = true;
    const fetchRates = async () => {
      const rates = await api.fetchForexRates();
      if (rates && rates.INR && isMounted) {
        setLiveInrRate(roundRate(rates.INR));
      }
    };

    const roundRate = (num: number) => Math.round(num * 100) / 100;

    fetchRates();
    const interval = setInterval(fetchRates, 60000); // 60s live forex refresh
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const setCurrency = (code: CurrencyCode) => {
    setCurrencyState(code);
    try {
      localStorage.setItem(STORAGE_KEY, code);
    } catch {}
  };

  const toggleCurrency = () => {
    setCurrency(currency === 'USD' ? 'INR' : 'USD');
  };

  const currencySymbol = currency === 'INR' ? '₹' : '$';
  const exchangeRate = currency === 'INR' ? liveInrRate : 1.0;

  const formatPrice = (amountInUSD: number, decimals?: number): string => {
    if (amountInUSD === undefined || amountInUSD === null || isNaN(amountInUSD)) {
      return `${currencySymbol}0.00`;
    }

    const converted = amountInUSD * exchangeRate;
    
    // Choose appropriate decimals based on magnitude if not explicitly provided
    let dec = decimals;
    if (dec === undefined) {
      if (Math.abs(converted) >= 100000) dec = 0;
      else if (Math.abs(converted) >= 100) dec = 2;
      else if (Math.abs(converted) >= 1) dec = 2;
      else dec = 4;
    }

    const locale = currency === 'INR' ? 'en-IN' : 'en-US';
    const formattedNum = converted.toLocaleString(locale, {
      minimumFractionDigits: dec,
      maximumFractionDigits: dec,
    });

    return `${currencySymbol}${formattedNum}`;
  };

  const formatRawNumber = (amountInUSD: number, decimals: number = 2): number => {
    const converted = amountInUSD * exchangeRate;
    const factor = Math.pow(10, decimals);
    return Math.round(converted * factor) / factor;
  };

  const value = useMemo(
    () => ({
      currency,
      currencySymbol,
      exchangeRate,
      liveInrRate,
      setCurrency,
      toggleCurrency,
      formatPrice,
      formatRawNumber,
    }),
    [currency, currencySymbol, exchangeRate, liveInrRate]
  );

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
};

export const useCurrency = (): CurrencyContextType => {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error('useCurrency must be used within a CurrencyProvider');
  }
  return context;
};
