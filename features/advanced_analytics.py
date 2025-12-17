"""
Advanced Analytics Module for Solar Performance Dashboard
========================================================
Machine Learning, Predictive Analytics, and Smart Insights
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, r2_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("⚠️ Scikit-learn not available. ML features disabled.")

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

class EnergyAnalytics:
    """Advanced analytics for energy data"""
    
    def __init__(self):
        self.models = {}
        self.scalers = {}
        self.feature_importance = {}
    
    def calculate_energy_efficiency(self, solar_df: pd.DataFrame, 
                                  factory_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive energy efficiency metrics"""
        
        if solar_df.empty or factory_df.empty:
            return {'efficiency': 0, 'self_sufficiency': 0, 'carbon_offset': 0}
        
        try:
            # Process solar data
            solar_daily = solar_df.groupby(solar_df['last_changed'].dt.date).agg({
                'total_kw': ['sum', 'mean', 'max']
            }).reset_index()
            solar_daily.columns = ['date', 'total_kwh', 'avg_kw', 'peak_kw']
            solar_daily['total_kwh'] = solar_daily['total_kwh'] / 4  # 15-min to hourly
            
            # Process factory data
            factory_daily = factory_df.groupby(factory_df['last_changed'].dt.date).agg({
                'daily_kwh': 'sum'
            }).reset_index()
            factory_daily.columns = ['date', 'consumption_kwh']
            
            # Merge data
            combined = pd.merge(solar_daily, factory_daily, on='date', how='inner')
            
            if combined.empty:
                return {'efficiency': 0, 'self_sufficiency': 0, 'carbon_offset': 0}
            
            # Calculate metrics
            total_solar = combined['total_kwh'].sum()
            total_consumption = combined['consumption_kwh'].sum()
            
            self_sufficiency = min((total_solar / total_consumption) * 100, 100) if total_consumption > 0 else 0
            
            # Energy efficiency (output per unit of solar capacity)
            installed_capacity = 50  # kW (update with actual capacity)
            theoretical_max = installed_capacity * 24 * len(combined)  # Max possible generation
            efficiency = (total_solar / theoretical_max) * 100 if theoretical_max > 0 else 0
            
            # Carbon offset (kg CO2)
            carbon_factor = 0.95  # kg CO2 per kWh (South Africa grid average)
            carbon_offset = total_solar * carbon_factor
            
            return {
                'efficiency': round(efficiency, 1),
                'self_sufficiency': round(self_sufficiency, 1), 
                'carbon_offset': round(carbon_offset, 0),
                'total_solar_kwh': round(total_solar, 0),
                'total_consumption_kwh': round(total_consumption, 0)
            }
            
        except Exception as e:
            print(f"Error calculating efficiency: {e}")
            return {'efficiency': 0, 'self_sufficiency': 0, 'carbon_offset': 0}
    
    def predict_energy_consumption(self, historical_data: pd.DataFrame, 
                                 days_ahead: int = 7) -> pd.DataFrame:
        """Predict future energy consumption using ML"""
        
        if not ML_AVAILABLE or historical_data.empty:
            # Return simple trend-based prediction
            return self._simple_trend_prediction(historical_data, days_ahead)
        
        try:
            # Prepare features
            df = historical_data.copy()
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Feature engineering
            df['day_of_week'] = df['date'].dt.dayofweek
            df['month'] = df['date'].dt.month
            df['day_of_month'] = df['date'].dt.day
            df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
            
            # Rolling averages
            df['consumption_7d'] = df['liters'].rolling(7, min_periods=1).mean()
            df['consumption_30d'] = df['liters'].rolling(30, min_periods=1).mean()
            
            # Lag features
            df['consumption_lag1'] = df['liters'].shift(1)
            df['consumption_lag7'] = df['liters'].shift(7)
            
            # Remove rows with NaN
            df = df.dropna()
            
            if len(df) < 14:  # Need minimum data
                return self._simple_trend_prediction(historical_data, days_ahead)
            
            # Prepare training data
            feature_cols = ['day_of_week', 'month', 'day_of_month', 'is_weekend',
                           'consumption_7d', 'consumption_30d', 'consumption_lag1', 'consumption_lag7']
            
            X = df[feature_cols]
            y = df['liters']
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)
            
            # Store model and scaler
            self.models['consumption'] = model
            self.scalers['consumption'] = scaler
            
            # Feature importance
            self.feature_importance['consumption'] = dict(zip(feature_cols, model.feature_importances_))
            
            # Generate predictions
            last_date = df['date'].max()
            future_dates = pd.date_range(start=last_date + timedelta(days=1), 
                                       periods=days_ahead, freq='D')
            
            predictions = []
            last_row = df.iloc[-1]
            
            for i, future_date in enumerate(future_dates):
                # Create features for prediction
                features = [
                    future_date.weekday(),  # day_of_week
                    future_date.month,      # month
                    future_date.day,        # day_of_month
                    int(future_date.weekday() >= 5),  # is_weekend
                    last_row['consumption_7d'],   # consumption_7d
                    last_row['consumption_30d'],  # consumption_30d
                    predictions[-1] if predictions else last_row['liters'],  # consumption_lag1
                    predictions[-7] if len(predictions) >= 7 else last_row['consumption_lag7']  # consumption_lag7
                ]
                
                # Scale and predict
                features_scaled = scaler.transform([features])
                prediction = model.predict(features_scaled)[0]
                predictions.append(max(0, prediction))  # Ensure non-negative
            
            # Create result DataFrame
            result = pd.DataFrame({
                'date': future_dates,
                'predicted_consumption': predictions,
                'confidence': 0.85  # Placeholder confidence score
            })
            
            return result
            
        except Exception as e:
            print(f"ML prediction failed: {e}")
            return self._simple_trend_prediction(historical_data, days_ahead)
    
    def _simple_trend_prediction(self, data: pd.DataFrame, days_ahead: int) -> pd.DataFrame:
        """Fallback simple trend-based prediction"""
        if data.empty:
            return pd.DataFrame()
        
        # Calculate simple moving average
        recent_data = data.tail(14)  # Last 2 weeks
        avg_consumption = recent_data['liters'].mean()
        
        # Add some seasonal variation
        future_dates = pd.date_range(
            start=pd.to_datetime(data['date'].max()) + timedelta(days=1),
            periods=days_ahead, 
            freq='D'
        )
        
        predictions = []
        for date in future_dates:
            # Weekend adjustment
            if date.weekday() >= 5:
                prediction = avg_consumption * 0.7  # Lower weekend usage
            else:
                prediction = avg_consumption
            predictions.append(prediction)
        
        return pd.DataFrame({
            'date': future_dates,
            'predicted_consumption': predictions,
            'confidence': 0.6
        })
    
    def detect_anomalies(self, data: pd.DataFrame, column: str = 'liters') -> pd.DataFrame:
        """Detect anomalies in energy data using statistical methods"""
        
        if data.empty or column not in data.columns:
            return pd.DataFrame()
        
        df = data.copy()
        values = df[column]
        
        # Calculate rolling statistics
        df['rolling_mean'] = values.rolling(window=7, min_periods=3).mean()
        df['rolling_std'] = values.rolling(window=7, min_periods=3).std()
        
        # Z-score method
        df['z_score'] = np.abs((values - df['rolling_mean']) / df['rolling_std'])
        
        # IQR method
        Q1 = values.quantile(0.25)
        Q3 = values.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        # Mark anomalies
        df['is_anomaly'] = (
            (df['z_score'] > 3) |  # Z-score > 3
            (values < lower_bound) |  # Below IQR lower bound
            (values > upper_bound)    # Above IQR upper bound
        )
        
        df['anomaly_type'] = 'normal'
        df.loc[(df['is_anomaly']) & (values > df['rolling_mean']), 'anomaly_type'] = 'high'
        df.loc[(df['is_anomaly']) & (values < df['rolling_mean']), 'anomaly_type'] = 'low'
        
        return df
    
    def calculate_cost_optimization(self, generator_data: pd.DataFrame,
                                  solar_data: pd.DataFrame) -> Dict[str, any]:
        """Calculate potential cost savings and optimizations"""
        
        optimizations = {
            'generator_savings': 0,
            'solar_improvements': 0,
            'load_shifting': 0,
            'recommendations': []
        }
        
        if generator_data.empty:
            return optimizations
        
        try:
            # Generator optimization
            avg_daily_fuel = generator_data['liters'].mean()
            avg_price = generator_data['price_per_litre'].mean() if 'price_per_litre' in generator_data.columns else 22.5
            
            # Calculate potential savings from efficiency improvements
            efficiency_improvement = 0.15  # 15% efficiency improvement potential
            monthly_generator_cost = avg_daily_fuel * avg_price * 30
            potential_generator_savings = monthly_generator_cost * efficiency_improvement
            
            optimizations['generator_savings'] = round(potential_generator_savings, 2)
            
            # Solar optimization
            if not solar_data.empty:
                current_solar = solar_data['total_kw'].sum() / 4  # Convert to kWh
                solar_potential = current_solar * 1.25  # 25% improvement potential
                kWh_value = 1.50  # R per kWh value
                potential_solar_value = (solar_potential - current_solar) * kWh_value
                optimizations['solar_improvements'] = round(potential_solar_value, 2)
            
            # Generate recommendations
            if avg_daily_fuel > 50:
                optimizations['recommendations'].append({
                    'type': 'generator',
                    'priority': 'high',
                    'action': 'Consider generator efficiency upgrade',
                    'potential_saving': f"R{potential_generator_savings:.0f}/month"
                })
            
            if optimizations['solar_improvements'] > 100:
                optimizations['recommendations'].append({
                    'type': 'solar',
                    'priority': 'medium',
                    'action': 'Solar panel cleaning and optimization',
                    'potential_saving': f"R{potential_solar_value:.0f}/month"
                })
            
            # Load shifting opportunity
            peak_hours = [7, 8, 9, 17, 18, 19]  # Typical peak hours
            load_shift_potential = 500  # R/month potential from load shifting
            optimizations['load_shifting'] = load_shift_potential
            
            if load_shift_potential > 0:
                optimizations['recommendations'].append({
                    'type': 'load_management',
                    'priority': 'medium', 
                    'action': 'Shift non-critical loads to off-peak hours',
                    'potential_saving': f"R{load_shift_potential:.0f}/month"
                })
            
        except Exception as e:
            print(f"Error in cost optimization: {e}")
        
        return optimizations
    
    def create_performance_score(self, metrics: Dict[str, float]) -> Dict[str, any]:
        """Calculate overall performance score and rating"""
        
        # Scoring weights
        weights = {
            'efficiency': 0.3,
            'self_sufficiency': 0.4, 
            'cost_effectiveness': 0.3
        }
        
        # Normalize metrics (0-100 scale)
        efficiency = min(metrics.get('efficiency', 0), 100)
        self_sufficiency = min(metrics.get('self_sufficiency', 0), 100)
        
        # Cost effectiveness (inverse of cost per kWh, normalized)
        cost_per_kwh = metrics.get('cost_per_kwh', 2.0)
        cost_effectiveness = max(0, 100 - (cost_per_kwh - 1.0) * 50)
        
        # Calculate weighted score
        performance_score = (
            efficiency * weights['efficiency'] +
            self_sufficiency * weights['self_sufficiency'] +
            cost_effectiveness * weights['cost_effectiveness']
        )
        
        # Determine rating
        if performance_score >= 90:
            rating = "Excellent"
            color = "green"
        elif performance_score >= 75:
            rating = "Good"
            color = "cyan"
        elif performance_score >= 60:
            rating = "Fair"
            color = "yellow"
        else:
            rating = "Needs Improvement"
            color = "red"
        
        return {
            'score': round(performance_score, 1),
            'rating': rating,
            'color': color,
            'components': {
                'efficiency': round(efficiency, 1),
                'self_sufficiency': round(self_sufficiency, 1),
                'cost_effectiveness': round(cost_effectiveness, 1)
            }
        }

def create_advanced_dashboard(analytics: EnergyAnalytics, 
                            solar_df: pd.DataFrame,
                            generator_df: pd.DataFrame, 
                            factory_df: pd.DataFrame) -> None:
    """Create advanced analytics dashboard section"""
    
    import streamlit as st
    
    st.markdown("## 🧠 Advanced Energy Intelligence")
    st.markdown("AI-powered insights and predictive analytics for optimal energy management")
    
    # Calculate advanced metrics
    efficiency_metrics = analytics.calculate_energy_efficiency(solar_df, factory_df)
    performance_score = analytics.create_performance_score(efficiency_metrics)
    
    # Performance Overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        from app_fixed import render_enhanced_metric
        render_enhanced_metric(
            "Performance Score",
            f"{performance_score['score']}/100",
            f"{performance_score['rating']}",
            performance_score['color'],
            "🎯"
        )
    
    with col2:
        render_enhanced_metric(
            "Energy Efficiency",
            f"{efficiency_metrics['efficiency']:.1f}%",
            "Solar system efficiency",
            "cyan",
            "⚡"
        )
    
    with col3:
        render_enhanced_metric(
            "Self-Sufficiency",
            f"{efficiency_metrics['self_sufficiency']:.1f}%",
            "Energy independence",
            "positive",
            "🔋"
        )
    
    with col4:
        render_enhanced_metric(
            "Carbon Offset",
            f"{efficiency_metrics['carbon_offset']:,.0f} kg",
            "CO₂ emissions avoided",
            "positive",
            "🌱"
        )
    
    # Predictive Analytics
    if not generator_df.empty:
        st.markdown("### 🔮 Predictive Analytics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Consumption prediction
            predictions = analytics.predict_energy_consumption(generator_df, 7)
            
            if not predictions.empty:
                # Create prediction chart
                fig = go.Figure()
                
                # Historical data (last 30 days)
                recent_data = generator_df.tail(30)
                fig.add_trace(go.Scatter(
                    x=recent_data['date'],
                    y=recent_data['liters'],
                    mode='lines+markers',
                    name='Historical',
                    line=dict(color='#3182ce')
                ))
                
                # Predictions
                fig.add_trace(go.Scatter(
                    x=predictions['date'],
                    y=predictions['predicted_consumption'],
                    mode='lines+markers',
                    name='Predicted',
                    line=dict(color='#f56565', dash='dash')
                ))
                
                fig.update_layout(
                    title="7-Day Fuel Consumption Forecast",
                    xaxis_title="Date",
                    yaxis_title="Consumption (Liters)",
                    height=400,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f7fafc')
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Anomaly detection
            anomaly_data = analytics.detect_anomalies(generator_df)
            
            if not anomaly_data.empty:
                anomalies = anomaly_data[anomaly_data['is_anomaly']]
                
                st.markdown(f"**🔍 Anomaly Detection**")
                st.metric("Anomalies Detected", len(anomalies))
                
                if len(anomalies) > 0:
                    st.markdown("**Recent Anomalies:**")
                    for _, anomaly in anomalies.tail(5).iterrows():
                        icon = "🔺" if anomaly['anomaly_type'] == 'high' else "🔻"
                        st.markdown(f"{icon} {anomaly['date']}: {anomaly['liters']:.1f}L ({anomaly['anomaly_type']})")
    
    # Cost Optimization
    st.markdown("### 💰 Cost Optimization Opportunities")
    
    optimization = analytics.calculate_cost_optimization(generator_df, solar_df)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        render_enhanced_metric(
            "Generator Savings",
            f"R {optimization['generator_savings']:,.0f}",
            "Monthly potential",
            "positive",
            "🔋"
        )
    
    with col2:
        render_enhanced_metric(
            "Solar Improvements",
            f"R {optimization['solar_improvements']:,.0f}",
            "Monthly potential", 
            "positive",
            "☀️"
        )
    
    with col3:
        render_enhanced_metric(
            "Load Shifting",
            f"R {optimization['load_shifting']:,.0f}",
            "Monthly potential",
            "positive",
            "⏰"
        )
    
    # Recommendations
    if optimization['recommendations']:
        st.markdown("### 🎯 AI Recommendations")
        
        for rec in optimization['recommendations']:
            priority_color = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }
            
            st.markdown(f"""
            **{priority_color[rec['priority']]} {rec['action']}**
            - Type: {rec['type'].title()}
            - Potential Saving: {rec['potential_saving']}
            """)
    
    # Model Performance (if ML is available)
    if ML_AVAILABLE and 'consumption' in analytics.feature_importance:
        st.markdown("### 📊 Model Insights")
        
        importance = analytics.feature_importance['consumption']
        
        # Feature importance chart
        features = list(importance.keys())
        importances = list(importance.values())
        
        fig = go.Figure(data=[
            go.Bar(x=importances, y=features, orientation='h',
                   marker_color='#38bdf8')
        ])
        
        fig.update_layout(
            title="Consumption Prediction - Feature Importance",
            xaxis_title="Importance",
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f7fafc')
        )
        
        st.plotly_chart(fig, use_container_width=True)