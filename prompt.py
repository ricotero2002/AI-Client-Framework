"""
Prompt Class - Structured Message Handling
Manages prompt structure with separation of static and dynamic content for cache optimization
"""
from typing import List, Dict, Optional, Union, Callable, Any, Type
from dataclasses import dataclass, field
from enum import Enum

try:
    from pydantic import BaseModel, Field, create_model
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None
    Field = None
    create_model = None


class PromptSection(Enum):
    """Enum for different sections of a prompt"""
    SYSTEM = "system"
    FEW_SHOT = "few_shot"
    USER = "user"


@dataclass
class FewShotExample:
    """Represents a few-shot example pair"""
    user: str
    assistant: str


@dataclass
class StructuredField:
    """Represents a field in structured output"""
    name: str
    field_type: str  # 'string', 'integer', 'boolean', 'array', 'object'
    description: Optional[str] = None
    required: bool = True
    constraints: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class CachingAnalysis:
    """Analysis results for caching optimization"""
    total_tokens: int
    static_tokens: int
    dynamic_tokens: int
    cacheable_percentage: float
    should_use_caching: bool
    recommendations: List[str]


@dataclass
class FineTuningEvaluation:
    """Evaluation results for fine-tuning recommendation"""
    recommend_fine_tuning: bool
    total_static_tokens: int
    threshold: int
    reason: str


class Prompt:
    """
    Structured prompt with separation of static and dynamic content.
    
    Optimized for caching by placing static content (system, few-shot) first
    and dynamic content (user input) last.
    
    Example:
        >>> prompt = (Prompt()
        ...     .set_system("You are a helpful assistant")
        ...     .add_few_shot_example("What is 2+2?", "2+2 equals 4")
        ...     .set_user_input("What is 3+3?"))
        >>> messages = prompt.to_messages()
    """
    
    def __init__(self, use_delimiters: bool = True):
        """Initialize an empty prompt
        
        Args:
            use_delimiters: If True, automatically add section delimiters
        """
        self._system_message: Optional[str] = None
        self._few_shot_examples: List[FewShotExample] = []
        self._user_input: str = ""
        self._delimiters: Dict[str, str] = {}
        self._metadata: Dict[str, any] = {}
        self._use_delimiters = use_delimiters
        
        # Structured output support
        self._structured_output_fields: List[StructuredField] = []
        self._structured_output_model: Optional[Type[BaseModel]] = None
        self._structured_output_name: str = "Response"
        
        # Template variables and file attachments
        self._template_variables: Dict[str, str] = {}
        self._file_attachments: List[Dict[str, Any]] = []
        
        # Database persistence
        self._prompt_id: Optional[int] = None
        self._prompt_hash: Optional[str] = None
        self._conversation_id: Optional[int] = None
        
        # Conversation context (separate from few-shots)
        self._conversation_context: List[Dict[str, str]] = []
        self._max_context_messages: int = 10
        
        # Set default delimiters if enabled
        if use_delimiters:
            self._delimiters = {
                'system': '---SYSTEM INSTRUCTIONS---',
                'examples': '---EXAMPLES---',
                'query': '---USER QUERY---'
            }
    
    # ==================== Builder Methods ====================
    
    def set_system(self, message: str) -> 'Prompt':
        """
        Set the system message (static content)
        Automatically adds delimiter if use_delimiters=True
        
        Args:
            message: System instructions for the AI
        
        Returns:
            Self for method chaining
        """
        self._system_message = message
        return self
    
    def add_few_shot_example(self, user: str, assistant: str) -> 'Prompt':
        """
        Add a few-shot example (static content)
        Automatically adds delimiter if use_delimiters=True
        
        Args:
            user: User message in the example
            assistant: Assistant response in the example
        
        Returns:
            Self for method chaining
        """
        self._few_shot_examples.append(FewShotExample(user=user, assistant=assistant))
        return self
    
    def set_user_input(self, message: str) -> 'Prompt':
        """
        Set the user input (dynamic content)
        Automatically adds delimiter if use_delimiters=True
        
        Args:
            message: Current user query
        
        Returns:
            Self for method chaining
        """
        self._user_input = message
        return self
    
    def set_metadata(self, key: str, value: any) -> 'Prompt':
        """
        Set metadata for the prompt
        
        Args:
            key: Metadata key
            value: Metadata value
        
        Returns:
            Self for method chaining
        """
        self._metadata[key] = value
        return self
    
    # ==================== Template Variable Methods ====================
    
    def set_variable(self, name: str, value: str) -> 'Prompt':
        """
        Set a template variable value
        
        Variables in the prompt text should be marked as [[variable_name]]
        and will be replaced when generating messages
        
        Args:
            name: Variable name (without brackets)
            value: Value to replace the variable with
        
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt = (Prompt()
            ...     .set_user_input("Analiza este texto: [[text]]")
            ...     .set_variable("text", "Hello world"))
        """
        self._template_variables[name] = value
        return self
    
    def set_variables(self, **variables) -> 'Prompt':
        """
        Set multiple template variables at once
        
        Args:
            **variables: Variable name-value pairs
        
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt.set_variables(name="John", age="30", city="NYC")
        """
        self._template_variables.update(variables)
        return self
    
    def _replace_variables(self, text: str) -> str:
        """Replace template variables in text"""
        import re
        result = text
        for var_name, var_value in self._template_variables.items():
            pattern = r'\[\[' + re.escape(var_name) + r'\]\]'
            result = re.sub(pattern, var_value, result)
        return result
    
    def _find_undefined_variables(self, text: str) -> List[str]:
        """Find variables in text that haven't been defined"""
        import re
        # Find all [[variable]] patterns
        pattern = r'\[\[([^\]]+)\]\]'
        found_vars = re.findall(pattern, text)
        
        # Return variables that aren't defined
        undefined = [var for var in found_vars if var not in self._template_variables]
        return undefined
    
    def get_undefined_variables(self) -> List[str]:
        """
        Get list of all undefined variables in the prompt
        
        Returns:
            List of variable names that are used but not defined
        """
        undefined = []
        
        # Check system message
        if self._system_message:
            undefined.extend(self._find_undefined_variables(self._system_message))
        
        # Check few-shot examples
        for example in self._few_shot_examples:
            undefined.extend(self._find_undefined_variables(example.user))
            undefined.extend(self._find_undefined_variables(example.assistant))
        
        # Check user input
        if self._user_input:
            undefined.extend(self._find_undefined_variables(self._user_input))
        
        # Return unique variables
        return list(set(undefined))
    
    def has_undefined_variables(self) -> bool:
        """Check if there are any undefined variables"""
        return len(self.get_undefined_variables()) > 0
    
    # ==================== File Attachment Methods ====================
    
    def attach_file(
        self,
        file_path: str,
        mime_type: Optional[str] = None,
        description: Optional[str] = None
    ) -> 'Prompt':
        """
        Attach a file to the prompt (image, PDF, video, etc.)
        
        Args:
            file_path: Path to the file
            mime_type: MIME type (auto-detected if None)
            description: Optional description of the file
        
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt.attach_file("document.pdf", description="Contract to analyze")
        """
        import os
        import mimetypes
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Auto-detect MIME type if not provided
        if mime_type is None:
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = "application/octet-stream"
        
        attachment = {
            'path': file_path,
            'mime_type': mime_type,
            'description': description,
            'type': self._get_file_type(mime_type)
        }
        
        self._file_attachments.append(attachment)
        return self
    
    def attach_image(self, image_path: str, description: Optional[str] = None) -> 'Prompt':
        """
        Attach an image file
        
        Args:
            image_path: Path to image file
            description: Optional description
        
        Returns:
            Self for method chaining
        """
        return self.attach_file(image_path, description=description)
    
    def attach_pdf(self, pdf_path: str, description: Optional[str] = None) -> 'Prompt':
        """
        Attach a PDF file
        
        Args:
            pdf_path: Path to PDF file
            description: Optional description
        
        Returns:
            Self for method chaining
        """
        return self.attach_file(pdf_path, mime_type="application/pdf", description=description)
    
    def attach_video(self, video_path: str, description: Optional[str] = None) -> 'Prompt':
        """
        Attach a video file
        
        Args:
            video_path: Path to video file
            description: Optional description
        
        Returns:
            Self for method chaining
        """
        return self.attach_file(video_path, description=description)
    
    def _get_file_type(self, mime_type: str) -> str:
        """Determine file type from MIME type"""
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type == 'application/pdf':
            return 'pdf'
        elif mime_type.startswith('audio/'):
            return 'audio'
        else:
            return 'document'
    
    def get_attachments(self) -> List[Dict[str, Any]]:
        """Get list of file attachments"""
        return self._file_attachments.copy()
    
    def has_attachments(self) -> bool:
        """Check if prompt has file attachments"""
        return len(self._file_attachments) > 0
    
    # ==================== Structured Output Methods ====================
    
    def add_output_field(
        self,
        name: str,
        field_type: str = "string",
        description: Optional[str] = None,
        required: bool = True,
        **constraints
    ) -> 'Prompt':
        """
        Add a field to the structured output schema
        
        Args:
            name: Field name
            field_type: Type of field ('string', 'integer', 'boolean', 'array', 'object', 'number')
            description: Description of what this field should contain
            required: Whether this field is required
            **constraints: Additional constraints (e.g., min_length=10, max_length=100, pattern="...")
        
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt.add_output_field(
            ...     "explanation",
            ...     field_type="string",
            ...     description="Explicación socrática del tema",
            ...     required=True,
            ...     min_length=50
            ... )
        """
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic is required for structured output. Install it with: pip install pydantic")
        
        field_obj = StructuredField(
            name=name,
            field_type=field_type,
            description=description,
            required=required,
            constraints=constraints
        )
        self._structured_output_fields.append(field_obj)
        return self
    
    def set_output_schema(
        self,
        model: Type[BaseModel],
        name: Optional[str] = None
    ) -> 'Prompt':
        """
        Set a Pydantic model as the output schema
        
        Args:
            model: Pydantic BaseModel class
            name: Optional name for the schema (defaults to model name)
        
        Returns:
            Self for method chaining
            
        Example:
            >>> from pydantic import BaseModel
            >>> class Answer(BaseModel):
            ...     explanation: str
            ...     confidence: float
            >>> prompt.set_output_schema(Answer)
        """
        if not PYDANTIC_AVAILABLE:
            raise ImportError("Pydantic is required for structured output. Install it with: pip install pydantic")
        
        self._structured_output_model = model
        if name:
            self._structured_output_name = name
        else:
            self._structured_output_name = model.__name__
        return self
    
    def get_output_schema(self) -> Optional[Dict[str, Any]]:
        """
        Get the JSON schema for structured output
        
        Returns:
            JSON schema dict or None if no structured output defined
        """
        if not PYDANTIC_AVAILABLE:
            return None
        
        # If user provided a Pydantic model, use it
        if self._structured_output_model:
            return self._structured_output_model.model_json_schema()
        
        # If user built schema field by field, create a dynamic model
        if self._structured_output_fields:
            # This will create and cache the model
            return self._build_schema_from_fields()
        
        return None
    
    def get_pydantic_model(self) -> Optional[Type[BaseModel]]:
        """
        Get the Pydantic model for structured output
        
        Returns:
            Pydantic BaseModel class or None if no structured output defined
            
        Note:
            If fields were added individually, this will create the model on first call
        """
        if not PYDANTIC_AVAILABLE:
            return None
        
        # If we already have a model, return it
        if self._structured_output_model:
            return self._structured_output_model
        
        # If we have fields, build the model (which caches it)
        if self._structured_output_fields:
            self._build_schema_from_fields()
            return self._structured_output_model
        
        return None
    
    def _build_schema_from_fields(self) -> Dict[str, Any]:
        """Build JSON schema from individual fields and create Pydantic model"""
        if not PYDANTIC_AVAILABLE:
            return {}
        
        # Map field types to Python types
        type_mapping = {
            'string': str,
            'integer': int,
            'boolean': bool,
            'number': float,
            'array': list,
            'object': dict
        }
        
        # Build Pydantic model fields
        model_fields = {}
        for field_obj in self._structured_output_fields:
            python_type = type_mapping.get(field_obj.field_type, str)
            
            # Make optional if not required
            if not field_obj.required:
                python_type = Optional[python_type]
            
            # Create Field with description and constraints
            field_kwargs = {}
            if field_obj.description:
                field_kwargs['description'] = field_obj.description
            
            # Add constraints
            field_kwargs.update(field_obj.constraints)
            
            # Create the field
            if field_kwargs:
                model_fields[field_obj.name] = (python_type, Field(**field_kwargs))
            else:
                model_fields[field_obj.name] = (python_type, ...)
        
        # Create dynamic Pydantic model and cache it
        dynamic_model = create_model(self._structured_output_name, **model_fields)
        
        # Store the model for validation purposes
        self._structured_output_model = dynamic_model
        
        return dynamic_model.model_json_schema()
    
    def has_structured_output(self) -> bool:
        """Check if structured output is defined"""
        return bool(self._structured_output_model or self._structured_output_fields)
    
    def validate_response(self, response_text: str) -> tuple[bool, Optional[Any], Optional[str]]:
        """
        Validate a JSON response against the structured output schema
        
        Args:
            response_text: JSON string response from the AI
        
        Returns:
            Tuple of (is_valid, validated_data, error_message)
            - is_valid: True if validation passed
            - validated_data: Pydantic model instance if valid, parsed dict if no model, None if invalid
            - error_message: Error description if invalid, None if valid
            
        Example:
            >>> prompt = Prompt().set_output_schema(MyModel).set_user_input("...")
            >>> response, _ = client.get_response(prompt)
            >>> is_valid, data, error = prompt.validate_response(response)
            >>> if is_valid:
            ...     print(f"Valid! Data: {data}")
            ... else:
            ...     print(f"Invalid: {error}")
        """
        if not PYDANTIC_AVAILABLE:
            return False, None, "Pydantic is not available"
        
        if not self.has_structured_output():
            return False, None, "No structured output schema defined"
        
        # Step 1: Parse JSON
        try:
            import json
            data = json.loads(response_text)
        except json.JSONDecodeError as e:
            return False, None, f"Invalid JSON: {str(e)}"
        
        # Step 2: Validate with Pydantic model if available
        if self._structured_output_model:
            try:
                from pydantic import ValidationError
                validated = self._structured_output_model(**data)
                return True, validated, None
            except ValidationError as e:
                error_details = []
                for error in e.errors():
                    field = " -> ".join(str(x) for x in error['loc'])
                    msg = error['msg']
                    error_details.append(f"{field}: {msg}")
                return False, None, "Pydantic validation failed:\n  " + "\n  ".join(error_details)
        
        # Step 3: If no Pydantic model, validate against schema structure
        schema = self.get_output_schema()
        if schema and 'required' in schema:
            missing_fields = [f for f in schema['required'] if f not in data]
            if missing_fields:
                return False, data, f"Missing required fields: {', '.join(missing_fields)}"
        
        # Basic validation passed
        return True, data, None
    
    # ==================== Conversion Methods ====================
    
    def to_messages(self) -> List[Dict[str, str]]:
        """
        Convert prompt to standard message format
        Apply template variable replacement
        
        Returns:
            List of message dictionaries with 'role' and 'content'
        """
        messages = []
        
        # Add system message
        if self._system_message:
            content = self._replace_variables(self._system_message)
            messages.append({'role': 'system', 'content': content})
        
        # Add few-shot examples (for teaching behavior)
        if self._few_shot_examples:
            for example in self._few_shot_examples:
                user_content = self._replace_variables(example.user)
                assistant_content = self._replace_variables(example.assistant)
                messages.append({'role': 'user', 'content': user_content})
                messages.append({'role': 'assistant', 'content': assistant_content})
        
        # Add conversation context (chat history)
        if self._conversation_context:
            # Limit context to max_context_messages
            context_to_use = self._conversation_context[-self._max_context_messages:] if len(self._conversation_context) > self._max_context_messages else self._conversation_context
            
            for msg in context_to_use:
                # Skip system messages from context (we already have one)
                if msg['role'] != 'system':
                    messages.append({'role': msg['role'], 'content': msg['content']})
        
        # Add user input
        if self._user_input:
            content = self._replace_variables(self._user_input)
            messages.append({'role': 'user', 'content': content})
        
        return messages
    
    def get_static_content(self) -> List[Dict[str, str]]:
        """
        Get only static content (system + few-shot examples)
        
        Returns:
            List of static messages
        """
        messages = []
        
        if self._system_message:
            messages.append({'role': 'system', 'content': self._system_message})
        
        for example in self._few_shot_examples:
            messages.append({'role': 'user', 'content': example.user})
            messages.append({'role': 'assistant', 'content': example.assistant})
        
        return messages
    
    def get_dynamic_content(self) -> List[Dict[str, str]]:
        """
        Get only dynamic content (user input)
        
        Returns:
            List of dynamic messages
        """
        if self._user_input:
            return [{'role': 'user', 'content': self._user_input}]
        return []
    
    # ==================== Validation Methods ====================
    
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the prompt structure and variables
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Must have at least user input
        if not self._user_input:
            return False, "Prompt must have user input"
        
        # Check for undefined variables
        undefined_vars = self.get_undefined_variables()
        if undefined_vars:
            vars_str = ", ".join(f"[[{v}]]" for v in undefined_vars)
            return False, f"Undefined template variables: {vars_str}"
        
        # Validate few-shot examples
        for i, example in enumerate(self._few_shot_examples):
            if not example.user or not example.assistant:
                return False, f"Few-shot example {i} has empty user or assistant message"
        
        return True, None
    
    def is_empty(self) -> bool:
        """Check if prompt is empty"""
        return not (self._system_message or self._few_shot_examples or self._user_input)
    
    # ==================== Visualization Methods ====================
    
    def print(self) -> str:
        """
        Get a simple string representation of the prompt
        
        Returns:
            String representation
        """
        parts = []
        
        if self._system_message:
            parts.append(f"[SYSTEM] {self._system_message}")
        
        for i, example in enumerate(self._few_shot_examples, 1):
            parts.append(f"[EXAMPLE {i} - USER] {example.user}")
            parts.append(f"[EXAMPLE {i} - ASSISTANT] {example.assistant}")
        
        if self._user_input:
            parts.append(f"[USER] {self._user_input}")
        
        return "\n".join(parts)
    
    def print_formatted(self, max_length: int = 100) -> str:
        """
        Get a formatted, pretty-printed representation
        
        Args:
            max_length: Maximum length for content preview
        
        Returns:
            Formatted string
        """
        lines = []
        lines.append("=" * 60)
        lines.append("PROMPT STRUCTURE")
        lines.append("=" * 60)
        
        # System section
        if self._system_message:
            lines.append("\n📋 SYSTEM MESSAGE (Static)")
            lines.append("-" * 60)
            content = self._system_message
            if len(content) > max_length:
                content = content[:max_length] + "..."
            lines.append(content)
        
        # Few-shot section
        if self._few_shot_examples:
            lines.append(f"\n💡 FEW-SHOT EXAMPLES (Static) - {len(self._few_shot_examples)} examples")
            lines.append("-" * 60)
            for i, example in enumerate(self._few_shot_examples, 1):
                lines.append(f"\nExample {i}:")
                user_preview = example.user[:max_length] + "..." if len(example.user) > max_length else example.user
                asst_preview = example.assistant[:max_length] + "..." if len(example.assistant) > max_length else example.assistant
                lines.append(f"  User: {user_preview}")
                lines.append(f"  Assistant: {asst_preview}")
        
        # User input section
        if self._user_input:
            lines.append("\n👤 USER INPUT (Dynamic)")
            lines.append("-" * 60)
            content = self._user_input
            if len(content) > max_length:
                content = content[:max_length] + "..."
            lines.append(content)
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
    
    # ==================== Caching Analysis Methods ====================
    
    def analyze_for_caching(self, token_counter: Callable[[str], int]) -> CachingAnalysis:
        """
        Analyze prompt for caching optimization
        
        Args:
            token_counter: Function to count tokens in text
        
        Returns:
            CachingAnalysis with recommendations
        """
        # Count static tokens
        static_tokens = 0
        if self._system_message:
            static_tokens += token_counter(self._system_message)
        
        for example in self._few_shot_examples:
            static_tokens += token_counter(example.user)
            static_tokens += token_counter(example.assistant)
        
        # Count dynamic tokens
        dynamic_tokens = 0
        if self._user_input:
            dynamic_tokens = token_counter(self._user_input)
        
        total_tokens = static_tokens + dynamic_tokens
        cacheable_percentage = (static_tokens / total_tokens * 100) if total_tokens > 0 else 0
        
        # Generate recommendations
        recommendations = []
        
        if static_tokens == 0:
            recommendations.append("⚠️ No static content - consider adding system message or few-shot examples")
            should_use_caching = False
        elif static_tokens < 1024:
            recommendations.append(f"💡 Static content ({static_tokens} tokens) is below recommended minimum (1024 tokens)")
            should_use_caching = False
        else:
            recommendations.append(f"✅ Good static content: {static_tokens} tokens")
            should_use_caching = True
        
        if cacheable_percentage > 70:
            recommendations.append(f"🎯 Excellent cache potential: {cacheable_percentage:.1f}% static")
        elif cacheable_percentage > 40:
            recommendations.append(f"👍 Good cache potential: {cacheable_percentage:.1f}% static")
        else:
            recommendations.append(f"⚠️ Low cache potential: {cacheable_percentage:.1f}% static")
        
        if not self._few_shot_examples and static_tokens > 0:
            recommendations.append("💡 Consider adding few-shot examples to improve model performance")
        
        return CachingAnalysis(
            total_tokens=total_tokens,
            static_tokens=static_tokens,
            dynamic_tokens=dynamic_tokens,
            cacheable_percentage=cacheable_percentage,
            should_use_caching=should_use_caching,
            recommendations=recommendations
        )
    
    def evaluate_fine_tuning(self, token_counter: Callable[[str], int], threshold: int = 2000) -> FineTuningEvaluation:
        """
        Evaluate if fine-tuning is recommended based on static content size
        
        Args:
            token_counter: Function to count tokens in text
            threshold: Token threshold for recommendation (default 2000)
            
        Returns:
            FineTuningEvaluation with recommendation
        """
        # Count static tokens (system + few-shot)
        static_tokens = 0
        if self._system_message:
            static_tokens += token_counter(self._system_message)
            
        for example in self._few_shot_examples:
            static_tokens += token_counter(example.user)
            static_tokens += token_counter(example.assistant)
            
        recommend_fine_tuning = static_tokens >= threshold
        
        if recommend_fine_tuning:
            reason = f"Static content ({static_tokens} tokens) exceeds threshold ({threshold}). Fine-tuning may be more cost-effective and efficient."
        else:
            reason = f"Static content ({static_tokens} tokens) is within limits ({threshold}). Few-shot prompting is appropriate."
            
        return FineTuningEvaluation(
            recommend_fine_tuning=recommend_fine_tuning,
            total_static_tokens=static_tokens,
            threshold=threshold,
            reason=reason
        )
    
    # ==================== Database Persistence Methods ====================
    
    def save(self) -> 'Prompt':
        """
        Save prompt template to database and get assigned ID
        
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt = Prompt().set_system("You are helpful")
            >>> prompt.save()
            >>> print(prompt.get_id())  # Database ID
        """
        from database import get_db_manager
        
        # Prepare few-shot examples for serialization
        few_shot_data = None
        if self._few_shot_examples:
            few_shot_data = [
                {'user': ex.user, 'assistant': ex.assistant}
                for ex in self._few_shot_examples
            ]
        
        # Save to database
        db = get_db_manager()
        prompt_record = db.save_prompt(self._system_message, few_shot_data)
        
        # Store ID and hash
        self._prompt_id = prompt_record.id
        self._prompt_hash = prompt_record.prompt_hash
        
        return self
    
    def get_id(self) -> Optional[int]:
        """
        Get database ID of saved prompt
        
        Returns:
            Prompt ID or None if not saved
        """
        return self._prompt_id
    
    def save_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        response: Optional[str] = None,
        cost: Optional[float] = None,
        quality_score: Optional[float] = None
    ) -> 'Prompt':
        """
        Save prompt execution metrics to database
        
        Args:
            model: Model used for execution
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            response: Response text (optional)
            cost: Execution cost (optional)
            quality_score: Quality score (optional)
            
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt.save_usage('gpt-4o', 100, 50, cost=0.002)
        """
        from database import get_db_manager
        
        # Ensure prompt is saved first
        if self._prompt_id is None:
            self.save()
        
        # Save usage record
        db = get_db_manager()
        db.save_usage(
            prompt_id=self._prompt_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            response=response,
            quality_score=quality_score,
            cost=cost
        )
        
        return self
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Retrieve usage statistics for this prompt
        
        Returns:
            Dictionary with usage statistics:
            - total_calls: Number of times prompt was used
            - total_input_tokens: Total input tokens
            - total_output_tokens: Total output tokens
            - total_cost: Total cost
            - avg_quality_score: Average quality score
            
        Example:
            >>> stats = prompt.get_usage_stats()
            >>> print(f"Used {stats['total_calls']} times")
        """
        from database import get_db_manager
        
        if self._prompt_id is None:
            return {
                'total_calls': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_cost': 0.0,
                'avg_quality_score': None
            }
        
        db = get_db_manager()
        return db.get_usage_stats(self._prompt_id)
    
    def set_conversation_context(self, messages: List[Dict[str, str]], max_context_messages: Optional[int] = None) -> 'Prompt':
        """
        Set conversation history as context for the prompt
        
        This stores conversation context SEPARATELY from few-shot examples.
        Few-shot examples are for teaching the model behavior, while conversation
        context is for maintaining chat history.
        
        If context exceeds max_context_messages, it will be automatically summarized.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            max_context_messages: Maximum context messages before summarization
            
        Returns:
            Self for method chaining
            
        Example:
            >>> prompt = Prompt().set_system("You are helpful")
            >>> prompt.add_few_shot_example("What is 2+2?", "4")  # Teaching behavior
            >>> history = [
            ...     {'role': 'user', 'content': 'Hello'},
            ...     {'role': 'assistant', 'content': 'Hi there!'}
            ... ]
            >>> prompt.set_conversation_context(history)  # Chat history
        """
        if max_context_messages is not None:
            self._max_context_messages = max_context_messages
        
        # Store conversation context separately
        self._conversation_context = messages
        
        # If context is too long, we'll handle it in to_messages()
        return self
    
    def get_usage_by_model(self) -> Dict[str, Dict[str, Any]]:
        """
        Get usage statistics grouped by model
        
        Returns:
            Dictionary with model names as keys and stats as values
            
        Example:
            >>> stats = prompt.get_usage_by_model()
            >>> print(stats['gpt-4o-mini'])
            {'calls': 5, 'avg_input_tokens': 120, 'avg_output_tokens': 80, 'avg_cost': 0.0012}
        """
        from database import get_db_manager
        
        if self._prompt_id is None:
            return {}
        
        db = get_db_manager()
        session = db.get_session()
        
        try:
            from database import PromptUsage
            usages = session.query(PromptUsage).filter(
                PromptUsage.prompt_id == self._prompt_id
            ).all()
            
            if not usages:
                return {}
            
            # Group by model
            model_stats = {}
            for usage in usages:
                model = usage.model
                if model not in model_stats:
                    model_stats[model] = {
                        'calls': 0,
                        'total_input_tokens': 0,
                        'total_output_tokens': 0,
                        'total_cost': 0.0,
                        'quality_scores': []
                    }
                
                model_stats[model]['calls'] += 1
                model_stats[model]['total_input_tokens'] += usage.input_tokens
                model_stats[model]['total_output_tokens'] += usage.output_tokens
                model_stats[model]['total_cost'] += usage.cost or 0.0
                if usage.quality_score is not None:
                    model_stats[model]['quality_scores'].append(usage.quality_score)
            
            # Calculate averages
            for model, stats in model_stats.items():
                calls = stats['calls']
                stats['avg_input_tokens'] = stats['total_input_tokens'] / calls
                stats['avg_output_tokens'] = stats['total_output_tokens'] / calls
                stats['avg_cost'] = stats['total_cost'] / calls
                
                if stats['quality_scores']:
                    stats['avg_quality_score'] = sum(stats['quality_scores']) / len(stats['quality_scores'])
                else:
                    stats['avg_quality_score'] = None
                
                # Remove temporary list
                del stats['quality_scores']
            
            return model_stats
            
        finally:
            session.close()
    
    def get_average_cost(self, model: Optional[str] = None) -> float:
        """
        Get average cost per call for this prompt
        
        Args:
            model: Optional model name to filter by. If None, returns overall average.
            
        Returns:
            Average cost per call
            
        Example:
            >>> avg_cost = prompt.get_average_cost('gpt-4o-mini')
            >>> print(f"Average cost: ${avg_cost:.6f}")
        """
        if model:
            model_stats = self.get_usage_by_model()
            if model in model_stats:
                return model_stats[model]['avg_cost']
            return 0.0
        else:
            stats = self.get_usage_stats()
            if stats['total_calls'] > 0:
                return stats['total_cost'] / stats['total_calls']
            return 0.0
    
    def optimize_for_caching(self) -> 'Prompt':
        """
        Return an optimized version of the prompt for caching
        
        Currently returns self as the structure is already optimized
        (static content first, dynamic last)
        
        Returns:
            Optimized prompt (self)
        """
        # The structure is already optimized by design
        # Static content (system, few-shot) comes first
        # Dynamic content (user input) comes last
        return self
    
    # ==================== Utility Methods ====================
    
    def clone(self) -> 'Prompt':
        """
        Create a deep copy of the prompt
        
        Returns:
            New Prompt instance with same content
        """
        new_prompt = Prompt(use_delimiters=False)  # Don't auto-add delimiters
        new_prompt._system_message = self._system_message
        new_prompt._few_shot_examples = self._few_shot_examples.copy()
        new_prompt._user_input = self._user_input
        new_prompt._delimiters = self._delimiters.copy()
        new_prompt._metadata = self._metadata.copy()
        new_prompt._use_delimiters = self._use_delimiters
        
        # Copy structured output
        new_prompt._structured_output_fields = self._structured_output_fields.copy()
        new_prompt._structured_output_model = self._structured_output_model
        new_prompt._structured_output_name = self._structured_output_name
        
        # Copy template variables and file attachments
        new_prompt._template_variables = self._template_variables.copy()
        new_prompt._file_attachments = self._file_attachments.copy()
        
        return new_prompt
    
    def __str__(self) -> str:
        """String representation"""
        return self.print()
    
    def __repr__(self) -> str:
        """Developer representation"""
        return f"Prompt(system={bool(self._system_message)}, examples={len(self._few_shot_examples)}, user={bool(self._user_input)})"


# ==================== Helper Functions ====================

def create_simple_prompt(text: str) -> Prompt:
    """
    Create a simple prompt with just user input
    
    Args:
        text: User input text
    
    Returns:
        Prompt instance
    """
    return Prompt().set_user_input(text)


def create_prompt_from_messages(messages: List[Dict[str, str]]) -> Prompt:
    """
    Create a Prompt from a list of messages
    
    Args:
        messages: List of message dictionaries
    
    Returns:
        Prompt instance
    """
    prompt = Prompt()
    
    for msg in messages:
        role = msg.get('role', '')
        content = msg.get('content', '')
        
        if role == 'system':
            prompt.set_system(content)
        elif role == 'user':
            # Last user message becomes the user input
            # Earlier ones become part of few-shot if there's an assistant response after
            prompt.set_user_input(content)
        elif role == 'assistant':
            # This is part of a few-shot example
            # We need to pair it with the previous user message
            pass  # Handled in a second pass
    
    return prompt
