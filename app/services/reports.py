import os
import tempfile
from datetime import datetime
from flask import current_app
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
import io
import tempfile

from app.models import Event, Guest, EventAttendance

def generate_bio_sheet(event_id):
    """
    Generate a bio sheet for an event.
    
    Args:
        event_id: ID of the event
        
    Returns:
        str: Path to the generated document
    """
    # Get the event and attendees
    event = Event.query.get_or_404(event_id)
    attendances = event.attendances.join(Guest).order_by(Guest.last_name, Guest.first_name).all()
    
    # Create a new document
    doc = Document()
    
    # Set document properties
    doc.core_properties.title = f"Bio Sheet - {event.name}"
    doc.core_properties.author = "Event Guest Manager"
    
    # Add header with event info
    header = doc.add_heading(f"{event.name} - Bio Sheet", level=1)
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add event details
    event_details = doc.add_paragraph()
    event_details.alignment = WD_ALIGN_PARAGRAPH.CENTER
    event_details.add_run(f"Date: {event.date.strftime('%B %d, %Y at %I:%M %p')}\n").bold = True
    if event.location:
        event_details.add_run(f"Location: {event.location}\n").bold = True
    event_details.add_run(f"Number of Attendees: {len(attendances)}").bold = True
    
    # Add some space
    doc.add_paragraph()
    
    # Add each attendee
    for i, attendance in enumerate(attendances):
        guest = attendance.guest
        
        # Add separator except for the first entry
        if i > 0:
            separator = doc.add_paragraph()
            separator.paragraph_format.space_before = Pt(10)
            separator.paragraph_format.space_after = Pt(10)
            separator_run = separator.add_run('* * * * *')
            separator_run.bold = True
            separator.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Create a table for the guest info
        table = doc.add_table(rows=1, cols=2)
        table.autofit = False
        table.allow_autofit = False
        
        # Set column widths
        table.columns[0].width = Inches(1.5)  # Photo column
        table.columns[1].width = Inches(5.0)  # Bio column
        
        # Get the cells
        photo_cell = table.cell(0, 0)
        bio_cell = table.cell(0, 1)
        
        # Add photo if available
        if guest.photo_filename:
            photo_path = os.path.join(current_app.config['UPLOAD_PATH'], guest.photo_filename)
            if os.path.exists(photo_path):
                try:
                    # Resize image for the document (about 1.5 inches wide)
                    img = Image.open(photo_path)
                    
                    # Calculate height based on aspect ratio to maintain ~1.5 inch width
                    aspect_ratio = img.height / img.width
                    target_width = 1.5  # in inches
                    target_height = target_width * aspect_ratio
                    
                    # Save to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp:
                        img.save(temp.name, format='JPEG', quality=95)
                        photo_paragraph = photo_cell.paragraphs[0]
                        photo_run = photo_paragraph.add_run()
                        photo_run.add_picture(temp.name, width=Inches(target_width), height=Inches(target_height))
                        os.unlink(temp.name)  # Delete the temp file
                except Exception as e:
                    current_app.logger.error(f"Error adding photo: {str(e)}")
        
        # Add guest information
        name_paragraph = bio_cell.paragraphs[0]
        name_run = name_paragraph.add_run(f"{guest.full_name}")
        name_run.bold = True
        name_run.font.size = Pt(14)
        
        if guest.title or guest.organization:
            title_org = []
            if guest.title:
                title_org.append(guest.title)
            if guest.organization:
                title_org.append(guest.organization)
            
            title_paragraph = bio_cell.add_paragraph()
            title_run = title_paragraph.add_run(", ".join(title_org))
            title_run.italic = True
            title_run.font.size = Pt(12)
        
        # Add the bio
        if guest.bio:
            bio_paragraph = bio_cell.add_paragraph()
            bio_paragraph.add_run(guest.bio)
        
        # Add donor capacity if available
        if guest.donor_capacity:
            capacity_paragraph = bio_cell.add_paragraph()
            capacity_paragraph.add_run("\nDonor Capacity: ").bold = True
            capacity_paragraph.add_run(guest.donor_capacity.replace('_', ' ').title())
        
        # Add notes from the attendance if available
        if attendance.notes:
            notes_paragraph = bio_cell.add_paragraph()
            notes_paragraph.add_run("\nEvent Notes: ").bold = True
            notes_paragraph.add_run(attendance.notes)
    
    # Create a temporary file for the document
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
        doc.save(temp_file.name)
        return temp_file.name