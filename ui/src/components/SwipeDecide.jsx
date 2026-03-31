import React, { useState, useEffect } from 'react';
import './SwipeDecide.css'; // I'll create this too

const SwipeDecide = () => {
    const [ideas, setIdeas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        fetch('/api/mission/ideas')
            .then(res => res.json())
            .then(data => {
                setIdeas(data.ideas || []);
                setLoading(false);
            })
            .catch(err => console.error("Loading ideas failed:", err));
    }, []);

    const handleSwipe = (action) => {
        if (currentIndex >= ideas.length) return;
        
        const idea = ideas[currentIndex];
        fetch('/api/mission/swipe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idea_id: idea.id, action })
        }).then(() => {
            setCurrentIndex(prev => prev + 1);
        });
    };

    if (loading) return <div className="loading">Mission Control Researching...</div>;
    if (currentIndex >= ideas.length) return <div className="empty">No more ideas. Check back later!</div>;

    const currentIdea = ideas[currentIndex];

    return (
        <div className="swipe-container">
            <div className="swipe-card">
                <div className="card-header">
                    <h3>{currentIdea.title}</h3>
                    <span className="score">Score: {currentIdea.score}</span>
                </div>
                <p className="desc">{currentIdea.desc}</p>
                <div className="actions">
                    <button className="btn pass" onClick={() => handleSwipe('PASS')}>Archived</button>
                    <button className="btn maybe" onClick={() => handleSwipe('MAYBE')}>Maybe</button>
                    <button className="btn yes" onClick={() => handleSwipe('YES')}>Yes</button>
                    <button className="btn now" onClick={() => handleSwipe('NOW')}>NOW!</button>
                </div>
            </div>
        </div>
    );
};

export default SwipeDecide;
