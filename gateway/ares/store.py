"""SQLite persistence: telemetry, witnesses, trust history, challenges, incidents."""
from __future__ import annotations

import json
import time

from sqlalchemy import Boolean, Column, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Telemetry(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True)
    node_id = Column(String, index=True)
    seq = Column(Integer)
    ts = Column(Integer)
    received_at = Column(Float, index=True)
    payload = Column(Text)
    hmac_ok = Column(Boolean)


class WitnessRow(Base):
    __tablename__ = "witness"
    id = Column(Integer, primary_key=True)
    node_id = Column(String, index=True)
    claim = Column(String, index=True)
    value = Column(Float)
    conf = Column(Float)
    received_at = Column(Float, index=True)
    hmac_ok = Column(Boolean)


class TrustHistory(Base):
    __tablename__ = "trust_history"
    id = Column(Integer, primary_key=True)
    node_id = Column(String, index=True)
    identity = Column(Float)
    integrity = Column(Float)
    consistency = Column(Float)
    overall = Column(Float)
    state = Column(String)
    at = Column(Float, index=True)


class Challenge(Base):
    __tablename__ = "challenges"
    id = Column(Integer, primary_key=True)
    challenge_id = Column(String, unique=True, index=True)
    node_id = Column(String, index=True)
    type = Column(String)
    nonce = Column(String)
    reason = Column(Text)
    issued_at = Column(Float)
    answered_at = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    detail = Column(Text, nullable=True)


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String, unique=True, index=True)
    claim = Column(String)
    summary = Column(Text)
    evidence = Column(Text)
    at = Column(Float, index=True)


class Store:
    def __init__(self, path: str = "ares.db") -> None:
        self.engine = create_engine(f"sqlite:///{path}", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)

    def add_telemetry(self, msg: dict, hmac_ok: bool) -> None:
        with self.Session() as s:
            s.add(Telemetry(node_id=msg.get("node_id"), seq=msg.get("seq"), ts=msg.get("ts"),
                            received_at=time.time(), payload=json.dumps(msg), hmac_ok=hmac_ok))
            s.commit()

    def add_witness(self, node_id: str, claim: str, value: float, conf: float, hmac_ok: bool) -> None:
        with self.Session() as s:
            s.add(WitnessRow(node_id=node_id, claim=claim, value=value, conf=conf,
                             received_at=time.time(), hmac_ok=hmac_ok))
            s.commit()

    def add_trust(self, node_id: str, identity: float, integrity: float, consistency: float,
                  overall: float, state: str) -> None:
        with self.Session() as s:
            s.add(TrustHistory(node_id=node_id, identity=identity, integrity=integrity,
                               consistency=consistency, overall=overall, state=state, at=time.time()))
            s.commit()

    def add_challenge(self, challenge_id: str, node_id: str, type_: str, nonce: str, reason: str) -> None:
        with self.Session() as s:
            s.add(Challenge(challenge_id=challenge_id, node_id=node_id, type=type_, nonce=nonce,
                            reason=reason, issued_at=time.time()))
            s.commit()

    def close_challenge(self, challenge_id: str, passed: bool, detail: str) -> None:
        with self.Session() as s:
            row = s.query(Challenge).filter_by(challenge_id=challenge_id).one_or_none()
            if row is not None:
                row.answered_at = time.time()
                row.passed = passed
                row.detail = detail
                s.commit()

    def add_incident(self, incident_id: str, claim: str, summary: str, evidence: dict) -> None:
        with self.Session() as s:
            s.add(Incident(incident_id=incident_id, claim=claim, summary=summary,
                           evidence=json.dumps(evidence), at=time.time()))
            s.commit()

    def get_incident(self, incident_id: str) -> dict | None:
        with self.Session() as s:
            row = s.query(Incident).filter_by(incident_id=incident_id).one_or_none()
            if row is None:
                return None
            return {"id": row.incident_id, "claim": row.claim, "summary": row.summary,
                    "evidence": json.loads(row.evidence or "{}"), "at": row.at}

    def recent_incidents(self, limit: int = 20) -> list[dict]:
        with self.Session() as s:
            rows = s.query(Incident).order_by(Incident.at.desc()).limit(limit).all()
            return [{"id": r.incident_id, "claim": r.claim, "summary": r.summary, "at": r.at} for r in rows]
