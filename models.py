from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from config import Config

Base = declarative_base()


class AOI(Base):
    """Area of Interest model."""
    __tablename__ = 'aois'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    geometry = Column(Text, nullable=False)  # GeoJSON string
    created_date = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    threshold_db = Column(Float, default=Config.CHANGE_THRESHOLD_DB)
    
    # Orbit properties (for consistent change detection)
    orbit_direction = Column(String(20), nullable=True)  # 'ASCENDING' or 'DESCENDING'
    relative_orbit_number = Column(Integer, nullable=True)  # Sentinel-1 relative orbit (1-175)
    platform_number = Column(String(10), nullable=True)  # 'A' or 'C' (Sentinel-1A/1C)
    
    # Relationships
    analyses = relationship('Analysis', back_populates='aoi', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<AOI {self.id}: {self.name}>'


class Analysis(Base):
    """Satellite image analysis record."""
    __tablename__ = 'analyses'
    
    id = Column(Integer, primary_key=True)
    aoi_id = Column(Integer, ForeignKey('aois.id'), nullable=False)
    
    # Image information
    reference_date = Column(DateTime, nullable=False)  # Previous image date
    new_image_date = Column(DateTime, nullable=False)  # New image date
    analysis_date = Column(DateTime, default=datetime.utcnow)  # When analysis was performed
    
    # Results
    changes_detected = Column(Boolean, default=False)
    change_score = Column(Float, default=0.0)  # Average change magnitude
    change_area_sqkm = Column(Float, default=0.0)
    change_percentage = Column(Float, default=0.0)
    
    # Outputs
    change_map_url = Column(String(512), nullable=True)  # GEE thumbnail URL
    ref_image_url = Column(String(512), nullable=True)  # Reference SAR image URL
    new_image_url = Column(String(512), nullable=True)  # New SAR image URL
    notes = Column(Text, nullable=True)
    
    # User feedback
    false_positive = Column(Boolean, default=False)
    user_notes = Column(Text, nullable=True)
    
    # Relationships
    aoi = relationship('AOI', back_populates='analyses')
    
    def __repr__(self):
        return f'<Analysis {self.id}: AOI {self.aoi_id} on {self.new_image_date}>'


# Database initialization
def init_db():
    """Initialize the database."""
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a database session."""
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    return Session()
