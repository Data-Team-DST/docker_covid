"""
Pipeline Executor pour Streamlit
Permet l'exécution étape par étape des pipelines sklearn avec mises à jour UI progressives.

Ce module résout le problème de l'exécution bloquante de sklearn.pipeline.Pipeline
en décomposant l'exécution en étapes individuelles, permettant à Streamlit de mettre
à jour l'interface utilisateur entre chaque transformateur.
"""

from typing import Generator, Tuple, Any, Optional
from sklearn.pipeline import Pipeline
import streamlit as st


class StreamlitPipelineExecutor:
    """
    Wrapper autour de sklearn.pipeline.Pipeline pour permettre l'exécution progressive
    avec mise à jour de l'UI Streamlit entre chaque étape.
    
    Cette classe décompose l'appel bloquant de pipeline.fit_transform() en une série
    d'appels individuels à chaque transformateur, avec des yields entre chaque étape
    pour permettre à Streamlit de rafraîchir l'interface.
    
    Usage:
        executor = StreamlitPipelineExecutor(pipeline)
        for step_idx, step_name, result in executor.execute_with_ui():
            # Mettre à jour l'UI entre chaque étape
            progress_bar.progress((step_idx + 1) / total_steps)
    """
    
    def __init__(self, pipeline: Pipeline, depth: int = 0):
        """
        Initialise l'exécuteur de pipeline.
        
        Args:
            pipeline: Instance de sklearn.pipeline.Pipeline à exécuter
            depth: Profondeur de récursion (0 = pipeline racine)
        """
        self.pipeline = pipeline
        self.step_containers = {}
        self.depth = depth
        
    def get_total_steps(self) -> int:
        """
        Retourne le nombre total d'étapes dans le pipeline.
        
        Returns:
            int: Nombre de transformateurs dans le pipeline
        """
        return len(self.pipeline.steps)
    
    def execute_with_ui(
        self, 
        X: Any = None,
        show_intermediate: bool = False,
        show_step_progress: bool = True
    ) -> Generator[Tuple[int, str, Any], None, None]:
        """
        Exécute le pipeline étape par étape avec mise à jour de l'UI.
        
        Cette méthode est un générateur qui yield après chaque transformateur,
        permettant à Streamlit de mettre à jour l'interface entre les étapes.
        
        Args:
            X: Données d'entrée pour le pipeline (peut être None)
            show_intermediate: Si True, affiche des infos sur les résultats intermédiaires
            show_step_progress: Si True, crée un container visuel pour chaque étape
        
        Yields:
            tuple: (step_index, step_name, intermediate_result)
                - step_index: Index de l'étape (0-based)
                - step_name: Nom du transformateur dans le pipeline
                - intermediate_result: Résultat de ce transformateur
        
        Example:
            executor = StreamlitPipelineExecutor(pipeline)
            for idx, name, result in executor.execute_with_ui():
                st.write(f"Completed step {idx}: {name}")
        """
        Xt = X
        total_steps = self.get_total_steps()
        
        for step_idx, (name, transformer) in enumerate(self.pipeline.steps):
            # Détecter si c'est un nested pipeline
            is_nested = isinstance(transformer, Pipeline)
            
            # Créer un container visuel pour cette étape si demandé
            if show_step_progress:
                # Pour nested pipeline, utiliser un expander, sinon container normal
                if is_nested:
                    # Nested pipeline: utiliser un expander avec indentation
                    indent = "  " * self.depth
                    container = st.expander(
                        f"{indent}🔗 **{name}** (Nested Pipeline - {len(transformer.steps)} étapes)",
                        expanded=True
                    )
                else:
                    container = st.container(border=True)
                
                self.step_containers[name] = container
                
                # Entrer dans le contexte du container AVANT de traiter son contenu
                with container:
                    if is_nested:
                        # Nested Pipeline: affichage dans l'expander
                        st.info(f"📦 Pipeline imbriqué avec {len(transformer.steps)} transformateurs")
                        
                        try:
                            # Créer un sous-executor avec profondeur +1
                            sub_executor = StreamlitPipelineExecutor(transformer, depth=self.depth + 1)
                            
                            # Exécuter récursivement (les widgets du sub-executor seront créés dans ce contexte)
                            for sub_idx, sub_name, sub_result in sub_executor.execute_with_ui(
                                Xt, 
                                show_intermediate=show_intermediate,
                                show_step_progress=True
                            ):
                                pass  # Laisser le sub-executor gérer l'affichage
                            
                            # Résultat final du nested pipeline
                            Xt = sub_result
                        
                        except Exception as e:
                            st.error(f"❌ Erreur dans le pipeline imbriqué: {e}")
                            raise
                    
                    else:
                        # Transformer normal: affichage classique
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Étape {step_idx + 1}/{total_steps}: {name}**")
                        with col2:
                            st.markdown(f"`{transformer.__class__.__name__}`")
                        
                        # Container pour la progression intra-transformateur
                        progress_container = st.empty()
                        
                        # Injecter le container dans le transformateur s'il supporte cette fonctionnalité
                        if hasattr(transformer, 'set_progress_container'):
                            transformer.set_progress_container(progress_container)
                        
                        # Indicateur de progression
                        step_status = st.empty()
                        step_status.info(f"⏳ En cours d'exécution...")
                        
                        try:
                            # Transformer normal: exécution classique
                            Xt = transformer.fit_transform(Xt)
                            
                            # Marquer comme complété
                            step_status.success(f"✅ Terminé")
                            
                            # Afficher les informations intermédiaires si demandé
                            if show_intermediate:
                                self._display_intermediate_info(Xt)
                        
                        except Exception as e:
                            step_status.error(f"❌ Erreur: {e}")
                            raise
            else:
                # Exécution sans interface visuelle détaillée
                Xt = transformer.fit_transform(Xt)
            
            # Yield pour permettre à Streamlit de mettre à jour l'UI
            yield step_idx, name, Xt
    
    def _display_intermediate_info(self, data: Any) -> None:
        """
        Affiche des informations sur le résultat intermédiaire.
        
        Args:
            data: Données à analyser et afficher
        """
        import pandas as pd
        import numpy as np
        
        info_text = []
        
        # Analyser selon le type
        if isinstance(data, pd.DataFrame):
            info_text.append(f"📊 DataFrame: {data.shape[0]} lignes × {data.shape[1]} colonnes")
            if 'label' in data.columns:
                label_counts = data['label'].value_counts()
                info_text.append(f"🏷️ Labels: {', '.join([f'{k} ({v})' for k, v in label_counts.items()])}")
        
        elif isinstance(data, np.ndarray):
            info_text.append(f"📊 Array: shape={data.shape}, dtype={data.dtype}")
            if data.size > 0:
                info_text.append(f"📈 Range: [{data.min():.2f}, {data.max():.2f}]")
        
        elif isinstance(data, dict):
            info_text.append(f"📦 Dictionnaire: {len(data)} clés")
            for key, value in list(data.items())[:3]:  # Limiter à 3 clés
                if isinstance(value, (list, tuple)):
                    info_text.append(f"   • {key}: {len(value)} items")
                else:
                    info_text.append(f"   • {key}: {type(value).__name__}")
        
        elif isinstance(data, (list, tuple)):
            info_text.append(f"📋 {type(data).__name__}: {len(data)} items")
        
        else:
            info_text.append(f"📦 Type: {type(data).__name__}")
        
        if info_text:
            with st.expander("ℹ️ Résultat intermédiaire", expanded=False):
                for line in info_text:
                    st.text(line)
    
    def execute_simple(self, X: Any = None) -> Any:
        """
        Exécute le pipeline de manière simple, sans générateur.
        
        Utile pour des cas où on veut juste la progression visuelle
        mais pas de contrôle étape par étape.
        
        Args:
            X: Données d'entrée
        
        Returns:
            Résultat final du pipeline
        """
        result = None
        for _, _, result in self.execute_with_ui(X, show_intermediate=False):
            pass  # Juste itérer jusqu'à la fin
        return result
